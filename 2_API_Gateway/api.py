"""
/etc/friends 통합 보안 게이트웨이 파이프라인 백엔드 (api.py - 고도화 버전)
- 1선 정책 통제: python-magic 기반 파일 시그니처(MIME) 검증
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
import magic
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse  # 파일 직접 리턴을 위해 추가
import torch

# MSA 구조 경로 인식 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

SRNET_DIR = os.path.join(BASE_DIR, "1_AI_Engine")
sys.path.append(SRNET_DIR)

from model.model import Srnet
from cdr_sanitizer import CDRSanitizer

app = FastAPI(title="/etc/friends Integrated Security Pipeline (In-Line Enhanced)")

# 디렉토리 아키텍처 정의 및 생성
WORKSPACE_DIR = os.path.join(BASE_DIR, "4_Local_Workspace")
UPLOAD_DIR = os.path.join(WORKSPACE_DIR, "uploads")
SANITIZED_DIR = os.path.join(WORKSPACE_DIR, "sanitized")
QUARANTINE_DIR = os.path.join(WORKSPACE_DIR, "quarantine")
DB_PATH = os.path.join(WORKSPACE_DIR, "stegano_audit.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SANITIZED_DIR, exist_ok=True)
os.makedirs(QUARANTINE_DIR, exist_ok=True)

# ─────────────────────────────────────────────────
# 데이터베이스 초기화 (SQLite3 방향성 컬럼 고도화)
# ─────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 인바운드/아웃바운드 통계를 위해 direction 컬럼 추가
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            direction TEXT,          -- INBOUND / OUTBOUND 추가
            original_name TEXT,
            stego_probability REAL,
            risk_level TEXT,
            verdict TEXT,
            action TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

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
    """대시보드 사이드바 시스템 정보 갱신 엔드포인트"""
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
    """인프라 가용성 및 내부 핵심 자산 무결성 진단"""
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
# 관제 통계 산출 엔드포인트 (양방향 데이터 세분화)
# ─────────────────────────────────────────────────
@app.get("/stats")
async def get_gateway_statistics():
    """보안팀 관제 대시보드 실시간 시각화용 데이터 통계 연산"""
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
        
        # 전체 검사 건수 및 위협 탐지 건수 실시간 연산
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN verdict='SUSPICIOUS' THEN 1 ELSE 0 END) FROM audit_logs")
        total, suspicious = cursor.fetchone()
        suspicious = suspicious if suspicious else 0
        
        # 리스크 등급별 통계 분포 데이터 추출
        cursor.execute("SELECT risk_level, COUNT(*) FROM audit_logs GROUP BY risk_level")
        risk_dist = dict(cursor.fetchall())

        # 방향성별(INBOUND / OUTBOUND) 트래픽 통계 추출
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
    """SQLite3에서 로그를 판독하여 대시보드 통계 및 감사 테이블로 전달"""
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
# 망연계 파일 통제 코어 파이프라인 라우터 (인라인 연동형)
# ─────────────────────────────────────────────────
@app.post("/scan")
async def scan_and_sanitize(
    file: UploadFile = File(...),
    direction: str = Form("INBOUND")  # mitmproxy에서 판별한 방향성 수신 추가
):
    """망연계 파일 통제 코어 파이프라인 라우터 (바이너리 리턴 구조)"""
    file_id = str(uuid.uuid4())[:8]
    contents = await file.read()
    
    # [Step 1: MIME 유형 검증 (정책 통제)]
    mime_type = magic.from_buffer(contents, mime=True)
    allowed_mimes = ["image/png", "image/jpeg"]
    
    if mime_type not in allowed_mimes:
        # 인라인 프록시 환경에서 정책 위반 시 브라우저 차단을 유도하도록 400 에러 처리
        raise HTTPException(
            status_code=400, 
            detail=f"Policy Violation: Unsupported file type ({mime_type}). Only PNG and JPEG are allowed."
        )

    # 순수 바이너리 스트림 유입 시 확장자 유실 방어 코드
    original_ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    input_filename = f"{file_id}_{file.filename or 'stream'}{original_ext}"
    input_path = os.path.join(UPLOAD_DIR, input_filename)
    
    with open(input_path, "wb") as f:
        f.write(contents)

    action = "BYPASS" # 초기화
    try:
        # [Step 2: AI 은닉 데이터 변조 탐지]
        from PIL import Image
        import numpy as np
        
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = img.crop((0, 0, 256, 256))
        
        img_array = np.array(img)
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).float() / 255.0
        img_tensor = img_tensor.unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(img_tensor)
            prob = torch.softmax(output, dim=1)[0]

        stego_prob_pct = prob[1].item() * 100
        
        # 위험 등급 분류 및 조치 액션 정의 (보안 민감도 30% 하향 튜닝 기준 적용)
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

        # [Step 3: CDR 무해화 프로세스 실행]
        output_filename = f"{file_id}_sanitized.jpg"
        output_path = os.path.join(SANITIZED_DIR, output_filename)
        cdr_info = sanitizer.sanitize(input_path, output_path)

        # [Step 4: 위협 파일 물리적 격리(Quarantine) 프로세스 실행]
        if action == "QUARANTINE":
            quarantine_path = os.path.join(QUARANTINE_DIR, input_filename)
            shutil.move(input_path, quarantine_path)
            try:
                os.chmod(quarantine_path, 0o440)  # Read-Only 설정 권한 제한
            except:
                pass

        # [Step 5: 감사 로그 영구 기록 (SQLite3 DB - direction 컬럼 반영)]
        timestamp_str = datetime.now().isoformat()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, direction, original_name, stego_probability, risk_level, verdict, action)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp_str, direction, file.filename or 'stream', round(stego_prob_pct, 1), risk_level, verdict, action))
        conn.commit()
        conn.close()

        # mitmproxy 연동용 커스텀 응답 헤더 탑재
        headers = {
            "X-Gateway-Verdict": str(verdict),
            "X-Gateway-Risk-Level": str(risk_level),
            "X-Gateway-Stego-Prob": f"{stego_prob_pct:.1f}%",
            "X-Gateway-File-ID": str(file_id)
        }

        # mitmproxy가 트래픽 바이너리를 그대로 주입할 수 있도록 무해화 파일 객체 즉시 반환
        return FileResponse(
            path=output_path,
            media_type="image/jpeg",
            headers=headers
        )

    except Exception as e:
        if os.path.exists(input_path) and action != "QUARANTINE":
            os.remove(input_path)
        raise HTTPException(status_code=500, detail=f"인라인 망연계 처리 실패: {str(e)}")