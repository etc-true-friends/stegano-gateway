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
import torch
import boto3

# MSA 구조 경로 인식 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

SRNET_DIR = os.path.join(BASE_DIR, "1_AI_Engine")
sys.path.append(SRNET_DIR)

from model.model import Srnet
from cdr_sanitizer import CDRSanitizer

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
# 망연계 파일 통제 코어 파이프라인 라우터
# ─────────────────────────────────────────────────
@app.post("/scan")
async def scan_and_sanitize(
    file: UploadFile = File(...),
    direction: str = Form("INBOUND")
):
    file_id = str(uuid.uuid4())[:8]
    contents = await file.read()
    
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
      <input type="file" id="outbound-file" accept="image/png,image/jpeg" onchange="handleOutbound(this)">
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
const PROXY_TARGET_OUTBOUND = 'http://3.88.139.96:8000/scan';

async function handleOutbound(input) {
  const file = input.files[0];
  if (!file) return;

  const preview = document.getElementById('outbound-preview');
  preview.src = URL.createObjectURL(file);
  preview.style.display = 'block';

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
