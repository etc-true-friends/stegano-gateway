"""
/etc/friends 통합 보안 게이트웨이 파이프라인 백엔드
- 1선 정책 통제: 바이너리 시그니처(imghdr) 기반 안전 검증
- 1선 AI 방어선: 파인튜닝된 SRNet 기반 은닉률 추론 (임계치 30% 반영)
- 2선 물리 방어선: CDR Sanitizer 기반 픽셀 구조 무해화 후 바이너리 스트림 반환
- 자산 통제: 위협 파일 격리(Quarantine) 및 접근 권한 제한
- 감사 통제: SQLite3 기반 관제 로그(방향성 포함) 영구 보존 및 지표 산출
"""

import io
import os
import sys
import uuid
import shutil
import sqlite3
import imghdr
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import PurePosixPath
import torch
import boto3
import json
import zipfile


# MSA 구조 경로 인식 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

SRNET_DIR = os.path.join(BASE_DIR, "1_AI_Engine")
sys.path.append(SRNET_DIR)

from model.model import Srnet
from cdr_sanitizer import CDRSanitizer
import auth

app = FastAPI(title="/etc/friends Integrated Security Pipeline (In-Line Enhanced)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

S3_BUCKET = os.getenv("S3_BUCKET")
s3 = boto3.client("s3")

# 디렉토리 아키텍처 정의 및 생성
WORKSPACE_DIR = os.path.join(BASE_DIR, "4_Local_Workspace")
UPLOAD_DIR = os.path.join(WORKSPACE_DIR, "uploads")
SANITIZED_DIR = os.path.join(WORKSPACE_DIR, "sanitized")
QUARANTINE_DIR = os.path.join(WORKSPACE_DIR, "quarantine")
DB_PATH = os.path.join(WORKSPACE_DIR, "stegano_audit.db")
MAIL_DB_PATH = os.path.join(CURRENT_DIR, "test.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SANITIZED_DIR, exist_ok=True)
os.makedirs(QUARANTINE_DIR, exist_ok=True)

# ─────────────────────────────────────────────────
# 데이터베이스 초기화 (SQLite3 방향성 컬럼 고도화)
# ─────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            direction TEXT,
            original_name TEXT,
            stego_probability REAL,
            risk_level TEXT,
            verdict TEXT,
            action TEXT
        )
    """)
    conn.commit()
    conn.close()

    auth.configure(DB_PATH)
    auth.init_employee_table()
    auth.seed_default_employee()

init_db()

app.include_router(auth.router)

# 하드웨어 및 인공지능 요원 초기화
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = Srnet().to(device)

CHECKPOINT_PATH = os.path.join(WORKSPACE_DIR, "checkpoints", "best_srnet_finetuned.pt")
if os.path.exists(CHECKPOINT_PATH):
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=False)
    state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    print("[+] API Gateway: 파인튜닝 완료된 SRNet 로드 성공.")
else:
    print(f"[-] 가중치 누락 경고: {CHECKPOINT_PATH}")

# 2선 방어선 CDR 무해화 요원 초기화
sanitizer = CDRSanitizer(jpeg_quality=85, resize_ratio=0.95)

@app.get("/")
def read_root():
    return {
        "ai_model": "SRNet (Finetuned v1.0)",
        "device": str(device),
        "version": "2026.05.22"
    }

# ─────────────────────────────────────────────────
# 시스템 상태 체크 엔드포인트
# ─────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    db_ok = os.path.exists(DB_PATH)
    quarantine_ok = os.path.exists(QUARANTINE_DIR)
    status = "healthy" if (db_ok and quarantine_ok) else "degraded"
    
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "infrastructure": {
            "database_connected": db_ok,
            "quarantine_storage": quarantine_ok
        }
    }

# ─────────────────────────────────────────────────
# 관제 통계 산출 엔드포인트
# ─────────────────────────────────────────────────
@app.get("/stats")
async def get_gateway_statistics():
    if not os.path.exists(DB_PATH):
        return {
            "total_traffic": 0,
            "threat_detected": 0,
            "bypass_count": 0,
            "risk_distribution": {},
            "direction_stats": {"INBOUND": 0, "OUTBOUND": 0}
        }
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN verdict='SUSPICIOUS' THEN 1 ELSE 0 END) FROM audit_logs")
        total, suspicious = cursor.fetchone()
        suspicious = suspicious if suspicious else 0
        
        cursor.execute("SELECT risk_level, COUNT(*) FROM audit_logs GROUP BY risk_level")
        risk_dist = dict(cursor.fetchall())

        cursor.execute("SELECT direction, COUNT(*) FROM audit_logs GROUP BY direction")
        dir_dist = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_traffic": total,
            "threat_detected": suspicious,
            "bypass_count": total - suspicious,
            "risk_distribution": risk_dist,
            "direction_stats": {
                "INBOUND": dir_dist.get("INBOUND", 0),
                "OUTBOUND": dir_dist.get("OUTBOUND", 0)
            },
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"지표 산출 실패: {str(e)}")

@app.get("/audit")
def get_audit():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, direction, original_name, stego_probability, risk_level, verdict, action FROM audit_logs")
    rows = cursor.fetchall()
    conn.close()

    logs = [dict(row) for row in rows]
    suspicious_count = sum(1 for log in logs if log["verdict"] == "SUSPICIOUS")
    
    return {
        "total_count": len(logs),
        "suspicious_count": suspicious_count,
        "logs": logs
    }
# ─────────────────────────────────────────────────
# 압축파일 내부 이미지 스캔/무해화 설정
# ─────────────────────────────────────────────────
ARCHIVE_MIMES = {
    "application/zip",
    "application/x-zip-compressed",
    "multipart/x-zip",
}

MAX_ARCHIVE_SIZE = int(os.getenv("MAX_ARCHIVE_SIZE", 50 * 1024 * 1024))  # 50MB
MAX_ARCHIVE_UNCOMPRESSED = int(os.getenv("MAX_ARCHIVE_UNCOMPRESSED", 200 * 1024 * 1024))  # 200MB
MAX_ARCHIVE_FILES = int(os.getenv("MAX_ARCHIVE_FILES", 200))
MAX_ARCHIVE_IMAGES = int(os.getenv("MAX_ARCHIVE_IMAGES", 100))
ALLOW_NON_IMAGE_IN_ARCHIVE = os.getenv("ALLOW_NON_IMAGE_IN_ARCHIVE", "false").lower() == "true"


def _safe_archive_member_name(name: str) -> str:
    """
    ZIP 내부 경로 검증.
    ../, 절대경로 등을 차단해서 Zip Slip 공격을 막는다.
    """
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)

    if path.is_absolute() or ".." in path.parts:
        raise HTTPException(status_code=400, detail=f"Unsafe archive path blocked: {name}")

    return str(path)


def _safe_disk_name(name: str) -> str:
    """
    파일명을 디스크에 저장 가능한 안전한 형태로 변환.
    """
    return "".join(
        c if c.isalnum() or c in "._-" else "_"
        for c in os.path.basename(name)
    )[:160]


def _record_audit(
    direction: str,
    original_name: str,
    stego_prob_pct: float,
    risk_level: str,
    verdict: str,
    action: str,
):
    """
    기존 audit_logs 테이블에 로그 저장.
    압축파일 내부 이미지 검사에서도 같은 로그 구조를 재사용한다.
    """
    timestamp_str = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs
        (timestamp, direction, original_name, stego_probability, risk_level, verdict, action)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp_str,
        direction,
        original_name,
        round(stego_prob_pct, 1),
        risk_level,
        verdict,
        action,
    ))
    conn.commit()
    conn.close()


def _scan_image_bytes(contents: bytes, display_name: str, direction: str, file_id: str):
    """
    이미지 파일 1개에 대해 기존 /scan과 같은 방식으로
    SRNet 분석 + CDR 무해화 + 감사 로그 저장을 수행한다.

    이 함수는 일반 이미지 업로드뿐 아니라 ZIP 내부 이미지 검사에서도 재사용할 수 있다.
    """
    img_format = imghdr.what(None, h=contents)

    if img_format not in ["png", "jpeg"]:
        raise ValueError(f"Unsupported image type: {img_format}")

    safe_name = _safe_disk_name(display_name) or "stream"
    original_ext = os.path.splitext(safe_name)[1] or f".{img_format}"

    input_filename = f"{file_id}_{safe_name}"

    if not os.path.splitext(input_filename)[1]:
        input_filename += original_ext

    input_path = os.path.join(UPLOAD_DIR, input_filename)

    with open(input_path, "wb") as f:
        f.write(contents)

    try:
        if S3_BUCKET:
            s3.upload_file(input_path, S3_BUCKET, f"uploads/{input_filename}")
    except Exception as e:
        print(f"S3 Upload Failed: {e}")

    from PIL import Image
    import numpy as np

    img = Image.open(io.BytesIO(contents)).convert("RGB")
    img = img.resize((256, 256))

    img_array = np.array(img)
    img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).float() / 255.0
    img_tensor = img_tensor.unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(img_tensor)
        prob = torch.softmax(output, dim=1)[0]

    stego_prob_pct = prob[1].item() * 100

    if stego_prob_pct >= 75.0:
        risk_level = "HIGH"
        verdict = "SUSPICIOUS"
        action = "QUARANTINE"
    elif stego_prob_pct >= 30.0:
        risk_level = "MEDIUM"
        verdict = "SUSPICIOUS"
        action = "QUARANTINE"
    else:
        risk_level = "LOW"
        verdict = "CLEAN"
        action = "BYPASS"

    output_filename = f"{file_id}_{os.path.splitext(safe_name)[0]}_sanitized.jpg"
    output_path = os.path.join(SANITIZED_DIR, output_filename)

    cdr_info = sanitizer.sanitize(input_path, output_path)

    try:
        if S3_BUCKET:
            s3.upload_file(output_path, S3_BUCKET, f"sanitized/{output_filename}")
    except Exception as e:
        print(f"S3 Upload Failed: {e}")

    if action == "QUARANTINE":
        quarantine_path = os.path.join(QUARANTINE_DIR, input_filename)
        shutil.move(input_path, quarantine_path)

        try:
            if S3_BUCKET:
                s3.upload_file(quarantine_path, S3_BUCKET, f"quarantine/{input_filename}")
        except Exception as e:
            print(f"S3 Upload Failed: {e}")

        try:
            os.chmod(quarantine_path, 0o440)
        except Exception:
            pass

    _record_audit(
        direction=direction,
        original_name=display_name,
        stego_prob_pct=stego_prob_pct,
        risk_level=risk_level,
        verdict=verdict,
        action=action,
    )

    return {
        "original_name": display_name,
        "stego_probability": round(stego_prob_pct, 1),
        "risk_level": risk_level,
        "verdict": verdict,
        "action": action,
        "sanitized_path": output_path,
        "cdr": cdr_info,
    }


def _scan_archive_bytes(contents: bytes, archive_name: str, direction: str, file_id: str):
    """
    ZIP 내부 이미지를 전부 검사하고,
    CDR 처리된 이미지들만 모아서 sanitized ZIP으로 다시 반환한다.
    """
    if len(contents) > MAX_ARCHIVE_SIZE:
        raise HTTPException(status_code=413, detail="Archive too large")

    if not zipfile.is_zipfile(io.BytesIO(contents)):
        raise HTTPException(status_code=400, detail="Unsupported archive format. ZIP only.")

    result_zip_name = f"{file_id}_{_safe_disk_name(os.path.splitext(archive_name)[0] or 'archive')}_sanitized.zip"
    result_zip_path = os.path.join(SANITIZED_DIR, result_zip_name)

    results = []
    suspicious_count = 0
    total_uncompressed = 0
    image_count = 0

    with zipfile.ZipFile(io.BytesIO(contents), "r") as zin, \
            zipfile.ZipFile(result_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:

        infos = zin.infolist()

        if len(infos) > MAX_ARCHIVE_FILES:
            raise HTTPException(status_code=413, detail="Too many files in archive")

        for info in infos:
            if info.is_dir():
                continue

            if info.flag_bits & 0x1:
                raise HTTPException(status_code=400, detail="Encrypted zip entries are not supported")

            member_name = _safe_archive_member_name(info.filename)

            total_uncompressed += info.file_size
            if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED:
                raise HTTPException(status_code=413, detail="Archive expands too large")

            raw = zin.read(info)
            img_format = imghdr.what(None, h=raw)

            if img_format in ["png", "jpeg"]:
                image_count += 1

                if image_count > MAX_ARCHIVE_IMAGES:
                    raise HTTPException(status_code=413, detail="Too many images in archive")

                scan_result = _scan_image_bytes(
                    raw,
                    display_name=f"{archive_name}::{member_name}",
                    direction=direction,
                    file_id=f"{file_id}_{image_count}",
                )

                results.append({
                    k: v for k, v in scan_result.items()
                    if k not in ["sanitized_path", "cdr"]
                })

                if scan_result["verdict"] == "SUSPICIOUS":
                    suspicious_count += 1

                out_member = str(PurePosixPath(member_name).with_suffix(".sanitized.jpg"))
                zout.write(scan_result["sanitized_path"], out_member)

            elif ALLOW_NON_IMAGE_IN_ARCHIVE:
                # 기본값 false.
                # 보안 게이트웨이 관점에서는 이미지 외 파일은 드롭하는 편이 안전하다.
                zout.writestr(member_name, raw)

    if image_count == 0:
        raise HTTPException(status_code=400, detail="No supported images found inside archive")

    overall_verdict = "SUSPICIOUS" if suspicious_count else "CLEAN"

    overall_risk = (
        "HIGH"
        if any(r["risk_level"] == "HIGH" for r in results)
        else ("MEDIUM" if suspicious_count else "LOW")
    )

    overall_action = "QUARANTINE" if suspicious_count else "BYPASS"
    max_prob = max(r["stego_probability"] for r in results)

    # 압축파일 전체 요약 로그 1개 추가.
    # 내부 이미지별 로그는 _scan_image_bytes()에서 이미 저장됨.
    _record_audit(
        direction=direction,
        original_name=archive_name,
        stego_prob_pct=max_prob,
        risk_level=overall_risk,
        verdict=overall_verdict,
        action=f"ARCHIVE_{overall_action}",
    )

    headers = {
        "X-Gateway-Verdict": overall_verdict,
        "X-Gateway-Risk-Level": overall_risk,
        "X-Gateway-Stego-Prob": f"{max_prob:.1f}%",
        "X-Gateway-File-ID": str(file_id),
        "X-Gateway-Archive-Images": str(image_count),
        "X-Gateway-Archive-Suspicious": str(suspicious_count),
        "X-Gateway-Archive-Mode": "ZIP_IMAGE_CDR",
        "Access-Control-Expose-Headers": "*",
    }

    return FileResponse(
        path=result_zip_path,
        filename=result_zip_name,
        media_type="application/zip",
        headers=headers,
    )
# ─────────────────────────────────────────────────
# 망연계 파일 통제 코어 파이프라인 라우터
# ─────────────────────────────────────────────────
@app.post("/scan")
async def scan_and_sanitize(
    file: UploadFile = File(...),
    direction: str = Form("INBOUND")
):
    file_id = str(uuid.uuid4())[:8]
    contents = await file.read()
    # ZIP 압축파일이면 내부 이미지들을 개별 스캔 + CDR 후 sanitized zip 반환
    content_type = (file.content_type or "").lower()
    filename_lower = (file.filename or "").lower()

    is_zip_payload = zipfile.is_zipfile(io.BytesIO(contents))

    if filename_lower.endswith(".zip") or content_type in ARCHIVE_MIMES or is_zip_payload:
      if not is_zip_payload:
        raise HTTPException(status_code=400, detail="Unsupported archive format. ZIP only.")

      return _scan_archive_bytes(
        contents,
        file.filename or "archive.zip",
        direction,
        file_id
    )
    
    # libmagic 의존성 우회: 내장 imghdr을 통한 안전한 포맷 검증
    img_format = imghdr.what(None, h=contents)
    if img_format not in ['png', 'jpeg']:
        raise HTTPException(
            status_code=400, 
            detail=f"Policy Violation: Unsupported file type ({img_format})."
        )

    original_ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    input_filename = f"{file_id}_{file.filename or 'stream'}{original_ext}"
    input_path = os.path.join(UPLOAD_DIR, input_filename)

    with open(input_path, "wb") as f:
        f.write(contents)

    try:
        s3.upload_file(
            input_path,
            S3_BUCKET,
            f"uploads/{input_filename}"
        )
    except Exception as e:
        print(f"S3 Upload Failed: {e}")

    action = "BYPASS"
    try:
        from PIL import Image
        import numpy as np
        
        # 차원 에러 방지: 투명도(RGBA)나 흑백을 강제로 RGB(3채널)로 고정 후 규격화
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = img.resize((256, 256)) 
        
        img_array = np.array(img)
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).float() / 255.0
        img_tensor = img_tensor.unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(img_tensor)
            prob = torch.softmax(output, dim=1)[0]

        stego_prob_pct = prob[1].item() * 100
        
        if stego_prob_pct >= 75.0:
            risk_level = "HIGH"
            verdict = "SUSPICIOUS"
            action = "QUARANTINE"
        elif stego_prob_pct >= 30.0:
            risk_level = "MEDIUM"
            verdict = "SUSPICIOUS"
            action = "QUARANTINE"
        else:
            risk_level = "LOW"
            verdict = "CLEAN"
            action = "BYPASS"

        output_filename = f"{file_id}_sanitized.jpg"
        output_path = os.path.join(SANITIZED_DIR, output_filename)

        cdr_info = sanitizer.sanitize(input_path, output_path)
        try:
            s3.upload_file(
                output_path,
                S3_BUCKET,
                f"sanitized/{output_filename}"
            )
        except Exception as e:
            print(f"S3 Upload Failed: {e}")

        if action == "QUARANTINE":
            quarantine_path = os.path.join(QUARANTINE_DIR, input_filename)

            shutil.move(input_path, quarantine_path)
            try:
                s3.upload_file(
                    quarantine_path,
                    S3_BUCKET,
                    f"quarantine/{input_filename}"
                )
            except Exception as e:
                print(f"S3 Upload Failed: {e}")

            try:
                os.chmod(quarantine_path, 0o440)
            except:
                pass

        timestamp_str = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, direction, original_name, stego_probability, risk_level, verdict, action)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp_str, direction, file.filename or 'stream', round(stego_prob_pct, 1), risk_level, verdict, action))
        conn.commit()
        conn.close()

        headers = {
            "X-Gateway-Verdict": str(verdict),
            "X-Gateway-Risk-Level": str(risk_level),
            "X-Gateway-Stego-Prob": f"{stego_prob_pct:.1f}%",
            "X-Gateway-File-ID": str(file_id),
            "Access-Control-Expose-Headers": "*"  # 브라우저 JS가 헤더를 읽을 수 있도록 허용
        }

        return FileResponse(
            path=output_path,
            media_type="image/jpeg",
            headers=headers
        )

    except Exception as e:
        if os.path.exists(input_path) and action != "QUARANTINE":
            os.remove(input_path)
        raise HTTPException(status_code=500, detail=f"인라인 망연계 처리 실패: {str(e)}")

# ─────────────────────────────────────────────────
# 직원 email 조회 엔드포인트
# ─────────────────────────────────────────────────
@app.get("/users/by-email")
def get_user_by_email(email: str):
    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, email, username
        FROM employee
        WHERE email = ? AND b_deleted = 'N'
        LIMIT 1
        """,
        (email.strip(),)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

    return {"id": row["id"], "email": row["email"], "username": row["username"]}


# ─────────────────────────────────────────────────
# 메일 전송 엔드포인트
# ─────────────────────────────────────────────────
@app.post("/mails/send")
async def send_mail(
        sender: str = Form(...),
        recipient: str = Form(...),
        subject: str = Form(...),
        body: str = Form(""),
        status: str = Form("SENT"),
        parent_mail_id: int | None = Form(None),
        attachments: list[UploadFile] = File(default=[]),
):
    now = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()

    sender_value = sender.strip()
    recipient_value = recipient.strip()

    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 발신자 username 조회
    cursor.execute("""
        SELECT id, username
        FROM employee
        WHERE username = ?
          AND b_deleted = 'N'
        LIMIT 1
    """, (sender_value,))
    sender_row = cursor.fetchone()

    if sender_row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="발신자를 찾을 수 없습니다.")

    sender_id = sender_row["id"]

    # 수신자 username 조회
    cursor.execute("""
        SELECT id, username
        FROM employee
        WHERE username = ?
          AND b_deleted = 'N'
        LIMIT 1
    """, (recipient_value,))
    recipient_row = cursor.fetchone()

    if recipient_row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="수신자를 찾을 수 없습니다.")

    recipient_id = recipient_row["id"]

    # 발신자 SENT 메일함 조회, 없으면 생성
    cursor.execute(
        "SELECT id FROM mailbox WHERE employee_id = ? AND type = 'SENT' LIMIT 1",
        (sender_id,)
    )
    row = cursor.fetchone()
    if row:
        mailbox_id = row["id"]
    else:
        cursor.execute(
            "INSERT INTO mailbox (employee_id, type, created_at) VALUES (?, 'SENT', ?)",
            (sender_id, now)
        )
        mailbox_id = cursor.lastrowid

    # 수신자 INBOX 메일함 조회, 없으면 생성
    cursor.execute(
        "SELECT id FROM mailbox WHERE employee_id = ? AND type = 'INBOX' LIMIT 1",
        (recipient_id,)
    )
    row = cursor.fetchone()
    if row:
        inbox_id = row["id"]
    else:
        cursor.execute(
            "INSERT INTO mailbox (employee_id, type, created_at) VALUES (?, 'INBOX', ?)",
            (recipient_id, now)
        )
        inbox_id = cursor.lastrowid

    final_status = status if status in ("SENT", "BLOCKED", "QUEUED", "SCANNING", "FAILED") else "SENT"

    # 발신자 SENT 메일함에 저장
    cursor.execute("""
        INSERT INTO mail (sender_id, mailbox_id, parent_mail_id, subject, body, status, sent_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (sender_id, mailbox_id, parent_mail_id, subject, body, final_status, now, now))
    mail_id = cursor.lastrowid

    # SENT인 경우에만 수신자 INBOX에도 저장
    if final_status == "SENT":
        cursor.execute("""
            INSERT INTO mail (sender_id, mailbox_id, parent_mail_id, subject, body, status, sent_at, created_at)
            VALUES (?, ?, ?, ?, ?, 'SENT', ?, ?)
        """, (sender_id, inbox_id, parent_mail_id, subject, body, now, now))

    saved_attachments = []
    for attachment in attachments:
        if not attachment.filename:
            continue

        file_id = str(uuid.uuid4())[:8]
        safe_name = _safe_disk_name(attachment.filename)
        stored_path = os.path.join(UPLOAD_DIR, f"{file_id}_{safe_name}")
        contents = await attachment.read()

        with open(stored_path, "wb") as f:
            f.write(contents)

        cursor.execute("""
            INSERT INTO mail_attachment (mail_id, original_file_name, stored_path, file_size, mime_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mail_id,
            attachment.filename,
            stored_path,
            len(contents),
            attachment.content_type,
            now
        ))

        saved_attachments.append({
            "original_file_name": attachment.filename,
            "file_size": len(contents),
            "mime_type": attachment.content_type,
        })

    conn.commit()
    conn.close()

    return {
        "id": mail_id,
        "sender": sender_value,
        "recipient": recipient_value,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "mailbox_id": mailbox_id,
        "subject": subject,
        "body": body,
        "status": final_status,
        "sent_at": now,
        "attachments": saved_attachments,
    }
# ─────────────────────────────────────────────────
# 메일 목록 조회
# GET /mails?type=inbox
# ─────────────────────────────────────────────────
@app.get("/mails")
async def get_mails(type: str = "inbox"):
    mailbox_type = type.upper()

    if mailbox_type == "INBOX":
        mailbox_type = "INBOX"
    elif mailbox_type == "sent":
        mailbox_type = "SENT"

    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            m.id AS mailId,
            e.username AS sender,
            m.subject AS subject,
            m.created_at AS createdAt,
            CASE
                WHEN COUNT(a.id) > 0 THEN 1
                ELSE 0
            END AS hasAttachment
        FROM mail m
        JOIN mailbox mb ON m.mailbox_id = mb.id
        JOIN employee e ON m.sender_id = e.id
        LEFT JOIN mail_attachment a ON m.id = a.mail_id
        WHERE mb.type = ?
        GROUP BY m.id
        ORDER BY m.created_at DESC
    """, (mailbox_type,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "mailId": row["mailId"],
            "sender": row["sender"],
            "subject": row["subject"],
            "hasAttachment": bool(row["hasAttachment"]),
            "createdAt": row["createdAt"]
        }
        for row in rows
    ]


# ─────────────────────────────────────────────────
# 메일 목록 조회 (test.db 기반: 받은 메일 -- 기본 뼈대 로직은 /mails/sent와 동일하게 처리합니다!)
# GET /mails/inbox?email=admin@gmail.com
# ─────────────────────────────────────────────────
@app.get("/mails/inbox")
async def get_inbox_mails(email: str = "admin@gmail.com"):
    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    login_email = email.strip()
    cur.execute(
        """
        SELECT id
        FROM employee
        WHERE email = ? AND b_deleted = 'N'
        LIMIT 1
        """,
        (login_email,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    employee_id = row["id"]

    rows = cur.execute(
        """
        SELECT
          m.id,
          m.subject,
          m.body,
          m.status,
          m.sent_at,
          e.username AS sender_username,
          e.email
        FROM mail m
        JOIN mailbox mb ON mb.id = m.mailbox_id
        JOIN employee e ON e.id = m.sender_id
        WHERE
          mb.employee_id = ?
          AND mb.type = 'INBOX'
          AND m.b_deleted = 'N'
        ORDER BY m.id DESC
        """,
        (employee_id,),
    ).fetchall()

    colors = ["primary.softBg", "success.softBg", "warning.softBg", "danger.softBg"]
    result = []
    for idx, r in enumerate(rows):
        rawBody = (r["body"] or "").strip()
        preview = rawBody.replace("\r\n", " ").replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:117] + "..."

        result.append(
            {
                "id": r["id"],
                "email": r["email"] or "",
                "sender": r["sender_username"] or "",
                "subject": r["subject"] or "",
                "preview": preview or (r["subject"] or ""),
                "date": r["sent_at"] or "",
                "unread": r["status"] == "SENT",
                "avatarColor": colors[idx % len(colors)],
            }
        )

    conn.close()
    return result

# ─────────────────────────────────────────────────
# 메일 목록 조회 (test.db 기반: 보낸 메일)
# GET /mails/sent?email=admin@gmail.com
# ─────────────────────────────────────────────────
@app.get("/mails/sent")
async def get_sent_mails(email: str = "admin@gmail.com"):
    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    login_email = email.strip()
    cur.execute(
        """
        SELECT id
        FROM employee
        WHERE email = ? AND b_deleted = 'N'
        LIMIT 1
        """,
        (login_email,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    employee_id = row["id"]

    rows = cur.execute(
        """
        SELECT
          m.id,
          m.subject,
          m.body,
          m.status,
          m.sent_at,
          e.username AS sender_username
        FROM mail m
        JOIN mailbox mb ON mb.id = m.mailbox_id
        JOIN employee e ON e.id = m.sender_id
        WHERE
          mb.employee_id = ?
          AND mb.type = 'SENT'
          AND m.b_deleted = 'N'
        ORDER BY m.id DESC
        """,
        (employee_id,),
    ).fetchall()

    colors = ["primary.softBg", "success.softBg", "warning.softBg", "danger.softBg"]
    result = []
    for idx, r in enumerate(rows):
        rawBody = (r["body"] or "").strip()
        preview = rawBody.replace("\r\n", " ").replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:117] + "..."

        result.append(
            {
                "id": r["id"],
                "sender": r["sender_username"] or "",
                "subject": r["subject"] or "",
                "preview": preview or (r["subject"] or ""),
                "date": r["sent_at"] or "",
                "unread": False,
                "avatarColor": colors[idx % len(colors)],
            }
        )

    conn.close()
    return result


# ─────────────────────────────────────────────────
# 받은 메일함 count 조회 (test.db 기반)
# GET /mails/inbox/count?email=admin@gmail.com
# ─────────────────────────────────────────────────
@app.get("/mails/inbox/count")
async def get_inbox_count(email: str = "admin@gmail.com"):
    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    login_email = email.strip()
    cur.execute(
        """
        SELECT id
        FROM employee
        WHERE email = ? AND b_deleted = 'N'
        LIMIT 1
        """,
        (login_email,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    employee_id = row["id"]

    cnt = cur.execute(
        """
        SELECT COUNT(*)
        FROM mail m
        JOIN mailbox mb ON mb.id = m.mailbox_id
        WHERE
          mb.employee_id = ?
          AND mb.type = 'INBOX'
          AND m.b_deleted = 'N'
          AND m.status = 'SENT'
        """,
        (employee_id,),
    ).fetchone()[0]

    conn.close()
    return {"inboxCount": int(cnt)}


# ─────────────────────────────────────────────────
# 받은 메일 읽음 처리
# PATCH /mails/{mail_id}/read
# ─────────────────────────────────────────────────
@app.patch("/mails/{mail_id}/read")
async def mark_mail_as_read(mail_id: int):
    conn = sqlite3.connect(MAIL_DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE mail
        SET status = 'READ'
        WHERE
          id = ?
          AND b_deleted = 'N'
          AND mailbox_id IN (
            SELECT id
            FROM mailbox
            WHERE type = 'INBOX'
          )
        """,
        (mail_id,),
    )

    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="읽음 처리할 받은 메일을 찾을 수 없습니다.")

    conn.commit()
    conn.close()
    return {"id": mail_id, "status": "READ"}


# ─────────────────────────────────────────────────
# 메일 상세 조회
# GET /mails/{id}
# ─────────────────────────────────────────────────
@app.get("/mails/{mail_id}")
async def get_mail_detail(mail_id: int):
    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            m.id AS mailId,
            sender.username AS sender,
            receiver.username AS receiver,
            m.subject AS subject,
            m.body AS body,
            m.created_at AS createdAt
        FROM mail m
        JOIN employee sender ON m.sender_id = sender.id
        JOIN mailbox mb ON m.mailbox_id = mb.id
        JOIN employee receiver ON mb.employee_id = receiver.id
        WHERE m.id = ?
        LIMIT 1
    """, (mail_id,))

    mail = cursor.fetchone()

    if mail is None:
        conn.close()
        raise HTTPException(status_code=404, detail="메일을 찾을 수 없습니다.")

    cursor.execute("""
        SELECT
            id AS attachmentId,
            original_file_name AS fileName
        FROM mail_attachment
        WHERE mail_id = ?
        ORDER BY id ASC
    """, (mail_id,))

    attachments = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        "mailId": mail["mailId"],
        "sender": mail["sender"],
        "receiver": mail["receiver"],
        "subject": mail["subject"],
        "body": mail["body"],
        "createdAt": mail["createdAt"],
        "attachments": attachments
    }


# ─────────────────────────────────────────────────
# 첨부파일 다운로드
# GET /attachments/{id}/download
# ─────────────────────────────────────────────────
@app.get("/attachments/{attachment_id}/download")
async def download_attachment(attachment_id: int):
    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            original_file_name,
            stored_path,
            mime_type
        FROM mail_attachment
        WHERE id = ?
        LIMIT 1
    """, (attachment_id,))

    attachment = cursor.fetchone()
    conn.close()

    if attachment is None:
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")

    stored_path = attachment["stored_path"]

    if not os.path.exists(stored_path):
        raise HTTPException(status_code=404, detail="첨부파일 파일이 서버에 존재하지 않습니다.")

    return FileResponse(
        path=stored_path,
        media_type=attachment["mime_type"] or "application/octet-stream",
        filename=attachment["original_file_name"]
    )

# ─────────────────────────────────────────────────
# 위협 현황 조회
# GET /threats
# ─────────────────────────────────────────────────
@app.get("/threats")
async def get_threats():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM audit_logs
        WHERE risk_level IN ('HIGH','MEDIUM')
    """)
    threats = [dict(row) for row in cursor.fetchall()]

    high_risk = sum(
        1 for t in threats
        if t["risk_level"] == "HIGH"
    )

    medium_risk = sum(
        1 for t in threats
        if t["risk_level"] == "MEDIUM"
    )

    blocked_files = sum(
        1 for t in threats
        if t["action"] == "QUARANTINE"
    )

    conn.close()

    return {
        "totalThreats": len(threats),
        "highRisk": high_risk,
        "mediumRisk": medium_risk,
        "blockedFiles": blocked_files,
        "recentThreats": threats[-10:]
    }


# ─────────────────────────────────────────────────
# CDR 처리 현황 조회
# GET /cdr/status
# audit_logs 테이블 기반으로 CDR 처리 현황 집계
# ─────────────────────────────────────────────────
@app.get("/cdr/status")
async def get_cdr_status():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM audit_logs
        WHERE action IN ('BYPASS', 'QUARANTINE', 'ARCHIVE_BYPASS', 'ARCHIVE_QUARANTINE')
        ORDER BY timestamp DESC
    """)
    cdr_logs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    total_processed = len(cdr_logs)

    sanitized_logs = [
        log for log in cdr_logs
        if log["action"] in ("BYPASS", "ARCHIVE_BYPASS")
    ]

    failed_logs = [
        log for log in cdr_logs
        if log["action"] in ("FAILED", "CDR_FAILED")
    ]

    success_rate = (
        round((len(sanitized_logs) / total_processed) * 100, 1)
        if total_processed > 0
        else 0.0
    )

    recent_cdr_logs = [
        {
            "id": log["id"],
            "fileName": log["original_name"],
            "status": log["action"],
            "processedAt": log["timestamp"]
        }
        for log in cdr_logs[:10]
    ]

    return {
        "totalProcessed": total_processed,
        "sanitized": len(sanitized_logs),
        "failed": len(failed_logs),
        "successRate": success_rate,
        "recentCdrLogs": recent_cdr_logs
    }

# ─────────────────────────────────────────────────
# 모의 망연계 포털 엔드포인트 (시연 최적화 UI 적용 및 이모지 제거)
# ─────────────────────────────────────────────────
@app.get("/portal", response_class=HTMLResponse)
async def portal():
    return """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>사내 망연계 파일 반출입 시스템</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0a0e14; color: #e8f0ea; min-height: 100vh; }
  .header { background: #0f1a12; border-bottom: 2px solid #00d992; padding: 20px 40px; display: flex; align-items: center; gap: 16px; }
  .header h1 { font-size: 20px; color: #00d992; font-family: monospace; }
  .header span { font-size: 13px; color: #6a8a72; }
  .container { max-width: 900px; margin: 48px auto; padding: 0 24px; }
  .card { background: #0f1a12; border: 1px solid #1a3325; border-radius: 8px; padding: 32px; margin-bottom: 24px; }
  .card h2 { font-size: 16px; color: #00d992; font-family: monospace; letter-spacing: 2px; margin-bottom: 8px; }
  .card p { font-size: 14px; color: #6a8a72; margin-bottom: 24px; }
  .upload-area { border: 2px dashed #1a3325; border-radius: 6px; padding: 32px; text-align: center; cursor: pointer; transition: border-color 0.2s; }
  .upload-area:hover { border-color: #00d992; }
  .upload-area input { display: none; }
  .upload-area label { cursor: pointer; }
  .upload-area p { color: #6a8a72; font-size: 14px; margin: 0; }
  .upload-area .icon { font-size: 24px; margin-bottom: 12px; font-weight: bold; color: #00d992; letter-spacing: 1px; }
  .btn { display: inline-block; padding: 12px 28px; border-radius: 5px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; font-family: monospace; letter-spacing: 1px; }
  .btn-green { background: #00d992; color: #0a0e14; }
  .btn-green:hover { background: #00b87a; }
  .btn-red { background: #ff4455; color: #fff; }
  .btn-red:hover { background: #cc2233; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  
  /* 시연용 AI 분석 결과 패널 스타일 */
  .result { margin-top: 20px; padding: 20px; border-radius: 8px; font-family: monospace; font-size: 14px; display: none; line-height: 1.6; }
  .result.clean { background: rgba(0,217,146,0.1); border: 1px solid #00d992; color: #e8f0ea; }
  .result.suspicious { background: rgba(255,68,85,0.1); border: 1px solid #ff4455; color: #e8f0ea; }
  .result.error { background: rgba(232,192,64,0.1); border: 1px solid #e8c040; color: #e8f0ea; }
  
  .ai-score-box { margin: 15px 0; padding: 15px; background: rgba(0,0,0,0.3); border-radius: 6px; border-left: 4px solid #fff; }
  .suspicious .ai-score-box { border-left-color: #ff4455; }
  .clean .ai-score-box { border-left-color: #00d992; }
  
  .score-title { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
  .score-value { font-size: 24px; font-weight: bold; }
  .suspicious .score-value { color: #ff4455; }
  .clean .score-value { color: #00d992; }

  .preview { max-width: 200px; max-height: 200px; border-radius: 4px; margin-top: 12px; border: 1px solid #1a3325; display: none; }
  .loading { display: none; color: #00d992; font-family: monospace; font-size: 14px; margin-top: 16px; font-weight: bold; }
  .loading-steps { font-size: 12px; color: #6a8a72; margin-top: 8px; font-weight: normal; }
  .download-list { display: flex; flex-direction: column; gap: 12px; }
  .download-item { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; background: #0a0e14; border: 1px solid #1a3325; border-radius: 5px; }
  .download-item .name { font-family: monospace; font-size: 13px; color: #e8f0ea; }
  .download-item .meta { font-size: 12px; color: #6a8a72; margin-top: 4px; }
</style>
</head>
<body>

<div class="header">
  <h1>// INTRANET FILE GATEWAY</h1>
  <span>사내 망연계 파일 반출입 시스템 | AI Stegano-Detector</span>
</div>

<div class="container">

  <div class="card">
    <h2>OUTBOUND — 파일 반출 (AI 검사 적용)</h2>
    <p>망연계 시스템을 통해 외부로 파일을 전송합니다. 전송 전 SRNet AI 엔진이 은닉 데이터를 검사합니다.</p>
    <div class="upload-area" onclick="document.getElementById('outbound-file').click()">
      <input type="file" id="outbound-file" accept="image/png,image/jpeg,application/zip,.zip" onchange="handleOutbound(this)">
      <label>
        <div class="icon">[ UPLOAD ]</div>
        <p>클릭하여 검사할 이미지 파일 선택</p>
        <p style="margin-top:6px; font-size:12px;">PNG, JPEG 지원 (자동 AI 스캔 진행)</p>
      </label>
    </div>
    <img id="outbound-preview" class="preview">
    
    <div class="loading" id="outbound-loading">
      [진행중] 게이트웨이 트래픽 인터셉트 및 AI 스캔 시작...
      <div class="loading-steps">
        > 1선 방어: 파일 시그니처 무결성 검증<br>
        > 1선 방어: SRNet 딥러닝 모델 텐서 변환 및 추론 중...
      </div>
    </div>
    
    <div class="result" id="outbound-result"></div>
  </div>

  <div class="card">
    <h2>INBOUND — 외부 파일 수신 (이메일 첨부파일 다운로드 모사)</h2>
    <p>외부 가상 메일 서버에 도착한 첨부파일 목록입니다. 다운로드 시 게이트웨이가 인라인으로 개입합니다.</p>
    <div class="download-list">
      <div class="download-item">
        <div>
          <div class="name">[첨부파일] attack_stego_report.png</div>
          <div class="meta">외부메일 첨부파일 · 1.5MB · 방금 전</div>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <button class="btn btn-green" onclick="downloadViaProxy('attack_stego_report.png')">보안 다운로드</button>
        </div>
      </div>
    </div>
    <div class="result" id="inbound-result" style="margin-top:16px;"></div>
  </div>

</div>

<script>
const PROXY_TARGET_OUTBOUND = '/scan';

async function handleOutbound(input) {
  const file = input.files[0];
  if (!file) return;

  const preview = document.getElementById('outbound-preview');

if (file.type.startsWith('image/')) {
  preview.src = URL.createObjectURL(file);
  preview.style.display = 'block';
} else {
  preview.removeAttribute('src');
  preview.style.display = 'none';
}

  const loading = document.getElementById('outbound-loading');
  const result = document.getElementById('outbound-result');
  loading.style.display = 'block';
  result.style.display = 'none';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(PROXY_TARGET_OUTBOUND, {
      method: 'POST',
      body: formData
    });
    
    loading.style.display = 'none';

    const verdict = res.headers.get('X-Gateway-Verdict');
    const prob = res.headers.get('X-Gateway-Stego-Prob') || '측정 불가';
    const risk = res.headers.get('X-Gateway-Risk-Level') || 'UNKNOWN';

    if (verdict === 'SUSPICIOUS' || res.status === 403) {
      result.className = 'result suspicious';
      result.innerHTML = `
        <strong style="color:#ff4455; font-size:16px;">[경고] 스테가노그래피 은닉 데이터 탐지</strong><br>
        1선 AI 방어선(SRNet)에서 비정상 픽셀 조작 패턴을 식별하여 파일 반출을 자동 차단했습니다.
        
        <div class="ai-score-box">
           <div class="score-title">SRNet AI Threat Score (은닉 확률)</div>
           <div class="score-value">${prob}</div>
           <div style="font-size:12px; margin-top:5px; color:#aaa;">판정 등급: ${risk} RISK (임계치 30% 초과)</div>
        </div>
        
        ▶ 조치 결과: 해당 세션 강제 종료 및 원본 파일 격리(Quarantine) 완료.
      `;
    } else {
      result.className = 'result clean';
      result.innerHTML = `
        <strong style="color:#00d992; font-size:16px;">[통과] 무해화(CDR) 전송 성공</strong><br>
        AI 엔진 스캔 결과, 위협 확률이 임계치 미만으로 확인되었습니다.
        
        <div class="ai-score-box">
           <div class="score-title">SRNet AI Threat Score (은닉 확률)</div>
           <div class="score-value">${prob}</div>
           <div style="font-size:12px; margin-top:5px; color:#aaa;">판정 등급: ${risk} RISK</div>
        </div>
        
        ▶ 조치 결과: 2선 물리 방어선(CDR)을 거쳐 픽셀 구조를 재구성한 뒤 안전하게 반출되었습니다.
      `;
    }
    result.style.display = 'block';
    
  } catch (e) {
    loading.style.display = 'none';
    result.className = 'result error';
    result.innerHTML = '[오류] 게이트웨이 연동 실패 — 프록시(mitmproxy) 또는 백엔드(api.py) 상태를 확인하세요.';
    result.style.display = 'block';
  }
}

async function downloadViaProxy(filename) {
  const result = document.getElementById('inbound-result');
  result.style.display = 'none';
  
  try {
    const res = await fetch(`${PROXY_TARGET_INBOUND}?file=${filename}`);
    
    const verdict = res.headers.get('X-Gateway-Verdict');
    
    if (verdict === 'SUSPICIOUS' || res.status === 403) {
      result.className = 'result suspicious';
      result.innerHTML = `[차단] 파일 반입 차단: 외부 메일 첨부파일 [${filename}] 내부에서 스테가노그래피 위협이 탐지되어 다운로드가 거부되었습니다.`;
    } else {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = "sanitized_" + filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      
      result.className = 'result clean';
      result.innerHTML = `[성공] 다운로드 완료: [${filename}] 파일 내부의 미세 변조 신호를 파괴(CDR 무해화)한 후 안전한 상태로 반입되었습니다.`;
    }
    result.style.display = 'block';
  } catch (e) {
    result.className = 'result error';
    result.innerHTML = '[오류] 게이트웨이 연동 실패 — 프록시 네트워크 설정을 확인하세요.';
    result.style.display = 'block';
  }
}
</script>
</body>
</html>
    """
