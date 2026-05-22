"""
/etc/friends 통합 보안 게이트웨이 파이프라인 백엔드 (api.py)
- 1선 정책 통제: python-magic 기반 파일 시그니처(MIME) 검증
- 1선 AI 방어선: 파인튜닝된 SRNet 기반 은닉률 추론
- 2선 물리 방어선: CDR Sanitizer 기반 픽셀 구조 무해화
- 자산 통제: 위협 파일 격리(Quarantine) 및 접근 권한 제한
- 감사 통제: SQLite3 기반 관제 로그 영구 보존
"""

import io
import os
import sys
import uuid
import shutil
import sqlite3
import magic
from datetime import datetime
from fastapi import FastAPI, UploadFile, File
import torch

# MSA 구조 경로 인식 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

SRNET_DIR = os.path.join(BASE_DIR, "1_AI_Engine")
sys.path.append(SRNET_DIR)

from model.model import Srnet
from cdr_sanitizer import CDRSanitizer

app = FastAPI(title="/etc/friends Integrated Security Pipeline")

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
# 데이터베이스 초기화 (SQLite3 영구 보존 뼈대)
# ─────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
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

@app.get("/audit")
def get_audit():
    """SQLite3에서 로그를 판독하여 대시보드 통계 및 감사 테이블로 전달"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, original_name, stego_probability, risk_level, verdict, action FROM audit_logs")
    rows = cursor.fetchall()
    conn.close()

    logs = [dict(row) for row in rows]
    suspicious_count = sum(1 for log in logs if log["verdict"] == "SUSPICIOUS")
    
    return {
        "total_count": len(logs),
        "suspicious_count": suspicious_count,
        "logs": logs
    }

@app.post("/scan")
async def scan_and_sanitize(file: UploadFile = File(...)):
    """망연계 파일 통제 코어 파이프라인 라우터"""
    file_id = str(uuid.uuid4())[:8]
    contents = await file.read()
    
    # [Step 1: MIME 유형 검증 (정책 통제 뼈대)]
    mime_type = magic.from_buffer(contents, mime=True)
    allowed_mimes = ["image/png", "image/jpeg"]
    
    if mime_type not in allowed_mimes:
        # 정책 위반 파일은 프로세스 조기 종료 및 격리 처리 없이 즉시 거부
        return {
            "status": "error",
            "message": f"Policy Violation: Unsupported file type ({mime_type}). Only PNG and JPEG are allowed."
        }

    input_filename = f"{file_id}_{file.filename}"
    input_path = os.path.join(UPLOAD_DIR, input_filename)
    with open(input_path, "wb") as f:
        f.write(contents)

    try:
        # [Step 2: AI 은닉 데이터 변조 탐지]
        import torch
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
            pred = output.data.max(1)[1].item()

        stego_prob_pct = prob[1].item() * 100
        
        # 위험 등급 분류 및 조치 액션 정의
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
            # 보안성 강화: 파일 권한을 Read-Only(440)로 하향 조정하여 무단 실행 및 변경 방지
            try:
                os.chmod(quarantine_path, 0o440)
            except:
                pass

        # [Step 5: 감사 로그 영구 기록 (SQLite3 DB 이식)]
        timestamp_str = datetime.now().isoformat()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, original_name, stego_probability, risk_level, verdict, action)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp_str, file.filename, round(stego_prob_pct, 1), risk_level, verdict, action))
        conn.commit()
        conn.close()

        return {
            "file_id": file_id,
            "pipeline": {
                "step1_detection": {
                    "stego_probability": f"{stego_prob_pct:.1f}%",
                    "risk_level": risk_level,
                    "verdict": verdict
                },
                "step2_sanitization": {
                    "steps": cdr_info["steps_executed"],
                    "pixel_diff": cdr_info["avg_pixel_diff"]
                },
                "step3_quarantine": {
                    "quarantined": True if action == "QUARANTINE" else False
                }
            }
        }

    except Exception as e:
        # 에러 발생 시 파일 무결성을 위해 생성 중이던 파일 파쇄
        if os.path.exists(input_path) and action != "QUARANTINE":
            os.remove(input_path)
        return {"status": "error", "message": str(e)}