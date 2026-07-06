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
import shlex
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import PurePosixPath
import torch
import boto3
import json
import zipfile
from urllib.parse import quote
import string
from collections import Counter

TORCH_NUM_THREADS = int(os.getenv("TORCH_NUM_THREADS", "1"))
TORCH_INTEROP_THREADS = int(os.getenv("TORCH_INTEROP_THREADS", "1"))
torch.set_num_threads(max(1, TORCH_NUM_THREADS))
try:
    torch.set_num_interop_threads(max(1, TORCH_INTEROP_THREADS))
except RuntimeError:
    pass


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

S3_BUCKET = os.getenv("S3_BUCKET", "stegano-gateway-storage-537124976047-us-east-1-an")
s3 = boto3.client("s3", region_name="us-east-1")

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            direction TEXT,
            original_name TEXT,
            stego_probability REAL,
            risk_level TEXT,
            verdict TEXT,
            action TEXT,
            file_id TEXT,
            sender_email TEXT,
            recipient_email TEXT,
            detection_engine TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cdr_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            file_name TEXT,
            stego_probability REAL,
            decoded_message TEXT,
            rescan_probability REAL,
            processed_at TEXT
        )
    """)
    # 탐지 임계값(격리/의심 경계)을 영속 저장하는 단일 행 테이블. id=1로 고정해 한 줄만 유지.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policy_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            high_threshold REAL NOT NULL,
            medium_threshold REAL NOT NULL
        )
    """)

    # 최초 1회만 기존 하드코딩 값(75.0/30.0)으로 시드. 이미 값이 있으면(OR IGNORE) 덮어쓰지 않음.
    cursor.execute(
        "INSERT OR IGNORE INTO policy_settings (id, high_threshold, medium_threshold) VALUES (1, 75.0, 30.0)"
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_metrics (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_views INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO dashboard_metrics (id, total_views)
        VALUES (1, 0)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_active_visitors (
            client_ip TEXT PRIMARY KEY,
            last_seen REAL NOT NULL
        )
    """)
    cursor.execute("PRAGMA table_info(audit_logs)")
    audit_columns = {row[1] for row in cursor.fetchall()}

    for column_name, column_type in {
        "file_id": "TEXT",
        "sender_email": "TEXT",
        "recipient_email": "TEXT",
        "detection_engine": "TEXT",   # 위험 판정에 기여한 탐지 엔진(SRNet Ensemble/Policy Engine/Hybrid Detection). 정상은 NULL.
    }.items():
        if column_name not in audit_columns:
            cursor.execute(f"ALTER TABLE audit_logs ADD COLUMN {column_name} {column_type}")

    # 무해화 이력 화면에서 쓰는 CDR 처리 상세를 cdr_logs에 누적 저장한다.
    cursor.execute("PRAGMA table_info(cdr_logs)")
    cdr_columns = {row[1] for row in cursor.fetchall()}

    for column_name, column_type in {
        "risk_level": "TEXT",          # 원본 위험도(HIGH/MEDIUM/LOW)
        "action": "TEXT",              # 처리 결과 액션(QUARANTINE/BYPASS 등)
        "original_kb": "REAL",         # 원본 크기(KB)
        "sanitized_kb": "REAL",        # 무해화 결과 크기(KB)
        "avg_pixel_diff": "REAL",      # 평균 픽셀 변화량(정화 강도 지표)
    }.items():
        if column_name not in cdr_columns:
            cursor.execute(f"ALTER TABLE cdr_logs ADD COLUMN {column_name} {column_type}")

    conn.commit()
    conn.close()

    auth.configure(DB_PATH)
    auth.init_employee_table()
    auth.seed_default_employee()

init_db()


def get_detection_thresholds() -> tuple[float, float]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT high_threshold, medium_threshold FROM policy_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (75.0, 30.0)


def set_detection_thresholds(high_threshold: float, medium_threshold: float) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE policy_settings SET high_threshold = ?, medium_threshold = ? WHERE id = 1",
        (high_threshold, medium_threshold),
    )
    conn.commit()
    conn.close()

app.include_router(auth.router)

# 하드웨어 및 인공지능 요원 초기화
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
MODELS_CONFIG_PATH = os.path.join(WORKSPACE_DIR, "models_config.json")


def _load_srnet_model(model_path: str):
    model_obj = Srnet().to(device)
    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
    model_obj.load_state_dict(state_dict, strict=True)
    model_obj.eval()
    return model_obj


def _resolve_model_path(config_dir: str, configured_path: str) -> str:
    if os.path.isabs(configured_path):
        return configured_path
    return os.path.abspath(os.path.join(config_dir, configured_path))


def _load_ensemble_models():
    if not os.path.exists(MODELS_CONFIG_PATH):
        print(f"[-] models_config.json not found: {MODELS_CONFIG_PATH}")
        return [], {"decision": {"mode": "single_fallback", "suspicious_margin": 0.15}}

    with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    config_dir = os.path.dirname(MODELS_CONFIG_PATH)
    loaded = []
    for item in config.get("models", []):
        if not item.get("enabled", True):
            continue

        model_path = _resolve_model_path(config_dir, item["path"])
        if not os.path.exists(model_path):
            print(f"[!] Ensemble model missing: {item.get('name')} -> {model_path}")
            continue

        loaded.append({
            "name": item["name"],
            "display_name": item.get("display_name", item["name"]),
            "threshold": float(item.get("threshold", 0.5)),
            "group": item.get("group", ""),
            "input_mode": item.get("input_mode", "rgb"),
            "path": model_path,
            "model": _load_srnet_model(model_path),
        })
        print(f"[+] Ensemble model loaded: {item['name']} ({model_path})")

    if not loaded:
        fallback_path = os.path.join(WORKSPACE_DIR, "checkpoints", "best_srnet_finetuned.pt")
        if os.path.exists(fallback_path):
            loaded.append({
                "name": "fallback_finetuned",
                "display_name": "Fallback finetuned SRNet",
                "threshold": 0.85,
                "group": "fallback",
                "path": fallback_path,
                "model": _load_srnet_model(fallback_path),
            })
            print(f"[+] Fallback SRNet model loaded: {fallback_path}")
        else:
            print("[-] No SRNet model could be loaded.")

    return loaded, config


ensemble_models, ensemble_config = _load_ensemble_models()

# 2선 방어선 CDR 무해화 요원 초기화
sanitizer = CDRSanitizer(jpeg_quality=85, resize_ratio=0.95)

ALETHEIA_TIMEOUT = float(os.getenv("ALETHEIA_TIMEOUT", "4"))
ALETHEIA_SUSPICIOUS_KEYWORDS = (
    "suspicious",
    "stego",
    "hidden",
    "detected",
    "positive",
    "embedding",
)
ALETHEIA_LOSSLESS_FORMATS = {"png", "bmp", "tiff", "tif"}
MULTICROP_ENABLED = os.getenv("MULTICROP_ENABLED", "true").lower() not in {"0", "false", "no"}
MULTICROP_MIN_SIDE = int(os.getenv("MULTICROP_MIN_SIDE", "512"))
MULTICROP_CROP_SIZE = int(os.getenv("MULTICROP_CROP_SIZE", "256"))
MULTICROP_STRIDE = int(os.getenv("MULTICROP_STRIDE", "384"))
MULTICROP_MAX_CROPS = int(os.getenv("MULTICROP_MAX_CROPS", "24"))
MULTICROP_TOP_K = int(os.getenv("MULTICROP_TOP_K", "3"))
MULTICROP_HIT_RATIO_THRESHOLD = float(os.getenv("MULTICROP_HIT_RATIO_THRESHOLD", "0.22"))
LOSSY_IMAGE_FORMATS = {"jpeg", "jpg", "webp"}


def _resolve_aletheia_command():
    configured = os.getenv("ALETHEIA_CMD")
    if configured:
        return shlex.split(configured)

    candidates = [
        ["aletheia.py", "auto"],
        ["aletheia", "auto"],
    ]
    for candidate in candidates:
        if shutil.which(candidate[0]):
            return candidate
    return None


def _run_aletheia(image_path: str, image_format: str | None = None) -> dict:
    """
    Run Aletheia steganalysis when the CLI is available.
    The gateway must keep serving files even if Aletheia is missing or fails.
    """
    normalized_format = (image_format or "").lower().replace("jpeg", "jpg")
    if normalized_format and normalized_format not in ALETHEIA_LOSSLESS_FORMATS:
        return {
            "available": True,
            "skipped": True,
            "suspicious": False,
            "reason": f"Aletheia SPA skipped for lossy image format: {normalized_format}",
        }

    command = _resolve_aletheia_command()
    if not command:
        return {
            "available": False,
            "suspicious": False,
            "reason": "Aletheia command not found",
        }

    try:
        completed = subprocess.run(
            command + [image_path],
            capture_output=True,
            text=True,
            timeout=ALETHEIA_TIMEOUT,
            check=False,
        )
        output = "\n".join(
            part for part in [completed.stdout, completed.stderr]
            if part
        ).strip()
        output_lower = output.lower()
        clean_markers = (
            "no hidden data found",
            "no stego",
            "not detected",
            "clean",
        )
        suspicious = (
            not any(marker in output_lower for marker in clean_markers)
            and any(
                keyword in output_lower
                for keyword in ALETHEIA_SUSPICIOUS_KEYWORDS
            )
        )

        return {
            "available": True,
            "suspicious": suspicious,
            "returncode": completed.returncode,
            "summary": output[:500],
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "suspicious": False,
            "reason": "Aletheia timeout",
        }
    except Exception as exc:
        return {
            "available": True,
            "suspicious": False,
            "reason": str(exc),
        }


def _crop_boxes(width: int, height: int, crop_size: int, stride: int, max_crops: int):
    if width <= crop_size and height <= crop_size:
        return [(0, 0, width, height)]

    xs = list(range(0, max(width - crop_size, 0) + 1, stride))
    ys = list(range(0, max(height - crop_size, 0) + 1, stride))
    if not xs or xs[-1] != max(width - crop_size, 0):
        xs.append(max(width - crop_size, 0))
    if not ys or ys[-1] != max(height - crop_size, 0):
        ys.append(max(height - crop_size, 0))

    boxes = [
        (x, y, min(x + crop_size, width), min(y + crop_size, height))
        for y in ys
        for x in xs
    ]
    if max_crops > 0 and len(boxes) > max_crops:
        import numpy as np
        keep = np.linspace(0, len(boxes) - 1, max_crops, dtype=np.int64)
        boxes = [boxes[int(i)] for i in keep]
    return boxes


def _image_to_model_tensor(img, input_mode: str):
    from PIL import Image
    import numpy as np

    img = img.convert("RGB")
    if img.size != (256, 256):
        resample = Image.Resampling.NEAREST if input_mode == "lsb" else Image.Resampling.BILINEAR
        img = img.resize((256, 256), resample)
    arr = np.array(img, dtype=np.uint8)
    if input_mode == "lsb":
        arr = (arr & 1).astype(np.float32)
    else:
        arr = arr.astype(np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)


def _aggregate_scores(values: list[float], mode: str = "topk_mean", top_k: int = MULTICROP_TOP_K) -> float:
    if not values:
        return 0.0
    ordered = sorted(values, reverse=True)
    if mode == "max":
        return ordered[0]
    if mode == "mean":
        return sum(ordered) / len(ordered)
    selected = ordered[: max(1, min(top_k, len(ordered)))]
    return sum(selected) / len(selected)


def _multicrop_policy_for_format(image_format: str | None) -> str:
    normalized = (image_format or "").lower().replace("jpg", "jpeg")
    return "mean" if normalized in LOSSY_IMAGE_FORMATS else "balanced"


def _is_multicrop_detected(row: dict, policy: str) -> bool:
    threshold = row["threshold"]
    if policy == "mean":
        return row["crop_mean"] >= threshold
    if policy == "balanced":
        return row["crop_mean"] >= threshold or (
            row["crop_topk"] >= threshold
            and row["crop_hit_ratio"] >= MULTICROP_HIT_RATIO_THRESHOLD
        )
    return row["probability"] >= threshold


def _predict_ensemble_image(img, image_format: str | None = None) -> dict:
    if not ensemble_models:
        return {
            "stego_prob_pct": 0.0,
            "route_model": "none",
            "high_detected": False,
            "suspicious_detected": False,
            "model_scores": [],
            "multicrop": {"enabled": False, "crop_count": 0},
        }

    suspicious_margin = float(
        ensemble_config.get("decision", {}).get("suspicious_margin", 0.15)
    )
    width, height = img.size
    use_multicrop = (
        MULTICROP_ENABLED
        and max(width, height) >= MULTICROP_MIN_SIDE
    )
    if use_multicrop:
        boxes = _crop_boxes(width, height, MULTICROP_CROP_SIZE, MULTICROP_STRIDE, MULTICROP_MAX_CROPS)
        if (0, 0, width, height) not in boxes:
            boxes.append((0, 0, width, height))
        decision_policy = _multicrop_policy_for_format(image_format)
    else:
        boxes = [(0, 0, width, height)]
        decision_policy = "aggregate"

    per_model_scores = {item["name"]: [] for item in ensemble_models}
    with torch.no_grad():
        for box in boxes:
            crop = img.crop(box)
            for item in ensemble_models:
                tensor = _image_to_model_tensor(crop, item.get("input_mode", "rgb"))
                output = item["model"](tensor)
                prob = torch.exp(output[:, 1])[0].item()
                per_model_scores[item["name"]].append(prob)

    scores = []
    for item in ensemble_models:
        values = per_model_scores[item["name"]]
        threshold = item["threshold"]
        probability = _aggregate_scores(values, "topk_mean", MULTICROP_TOP_K)
        crop_mean = sum(values) / len(values) if values else 0.0
        crop_topk = _aggregate_scores(values, "topk_mean", MULTICROP_TOP_K)
        crop_max = max(values) if values else 0.0
        decision_probability = crop_mean if decision_policy == "mean" else probability
        hit_count = sum(1 for value in values if value >= threshold)
        hit_ratio = hit_count / len(values) if values else 0.0
        row = {
            "name": item["name"],
            "display_name": item["display_name"],
            "probability": probability,
            "probability_pct": probability * 100.0,
            "decision_probability": decision_probability,
            "decision_probability_pct": decision_probability * 100.0,
            "threshold": threshold,
            "threshold_pct": threshold * 100.0,
            "suspicious_detected": False,
            "router_score": decision_probability / max(threshold, 1e-9),
            "input_mode": item.get("input_mode", "rgb"),
            "crop_max_pct": crop_max * 100.0,
            "crop_mean": crop_mean,
            "crop_mean_pct": crop_mean * 100.0,
            "crop_topk": crop_topk,
            "crop_topk_pct": crop_topk * 100.0,
            "crop_hit_count": hit_count,
            "crop_hit_ratio_pct": hit_ratio * 100.0,
            "crop_hit_ratio": hit_ratio,
        }
        row["high_detected"] = _is_multicrop_detected(row, decision_policy)
        row["suspicious_detected"] = (
            row["high_detected"]
            if use_multicrop
            else decision_probability >= max(0.0, threshold - suspicious_margin)
        )
        scores.append(row)

    route = max(
        scores,
        key=lambda row: (
            int(row["high_detected"]),
            row["router_score"],
            row["probability"] / max(row["threshold"], 1e-9),
        ),
    )
    return {
        "stego_prob_pct": route["decision_probability_pct"],
        "route_model": route["name"],
        "route_display_name": route["display_name"],
        "route_threshold_pct": route["threshold_pct"],
        "high_detected": any(row["high_detected"] for row in scores),
        "suspicious_detected": any(row["suspicious_detected"] for row in scores),
        "model_scores": scores,
        "multicrop": {
            "enabled": use_multicrop,
            "crop_count": len(boxes),
            "decision_policy": decision_policy,
            "hit_ratio_threshold_pct": MULTICROP_HIT_RATIO_THRESHOLD * 100.0,
        },
    }


def _predict_ensemble(img_tensor: torch.Tensor) -> dict:
    if not ensemble_models:
        return {
            "stego_prob_pct": 0.0,
            "route_model": "none",
            "high_detected": False,
            "suspicious_detected": False,
            "model_scores": [],
        }

    suspicious_margin = float(
        ensemble_config.get("decision", {}).get("suspicious_margin", 0.15)
    )

    scores = []
    with torch.no_grad():
        for item in ensemble_models:
            output = item["model"](img_tensor)
            prob = torch.exp(output[:, 1])[0].item()
            threshold = item["threshold"]
            scores.append({
                "name": item["name"],
                "display_name": item["display_name"],
                "probability": prob,
                "probability_pct": prob * 100.0,
                "threshold": threshold,
                "threshold_pct": threshold * 100.0,
                "high_detected": prob >= threshold,
                "suspicious_detected": prob >= max(0.0, threshold - suspicious_margin),
                "router_score": prob / max(threshold, 1e-9),
            })

    route = max(scores, key=lambda row: row["router_score"])

    return {
        "stego_prob_pct": route["probability_pct"],
        "route_model": route["name"],
        "route_display_name": route["display_name"],
        "route_threshold_pct": route["threshold_pct"],
        "high_detected": any(row["high_detected"] for row in scores),
        "suspicious_detected": any(row["suspicious_detected"] for row in scores),
        "model_scores": scores,
    }


# 감사 로그 "탐지 엔진" 컬럼 라벨. 정상 로그는 None(빈값)으로 남긴다.
ENGINE_SRNET = "SRNet Ensemble"      # AI 앙상블 단독 위험 판정
ENGINE_POLICY = "Policy Engine"      # 위험/이중 확장자, ZIP 내부 위험 파일 등 정책 처리
ENGINE_HYBRID = "Hybrid Detection"   # SRNet/Aletheia 등 복합 기여 또는 Aletheia 단독(분리 애매)


def _classify_scan(
    stego_prob_pct: float,
    aletheia_result: dict,
    ensemble_result: dict | None = None,
    high_threshold: float = 75.0,
    medium_threshold: float = 30.0,
):
    aletheia_suspicious = bool(aletheia_result.get("suspicious"))
    ensemble_high = bool(ensemble_result and ensemble_result.get("high_detected"))
    ensemble_suspicious = bool(ensemble_result and ensemble_result.get("suspicious_detected"))
    multicrop_enabled = bool(
        ensemble_result
        and ensemble_result.get("multicrop", {}).get("enabled")
    )

    # 탐지 엔진 귀속:
    # - Aletheia가 관여하면 SRNet과의 분리가 애매하므로 Hybrid Detection으로 묶는다.
    # - 그 외 AI 앙상블 단독 판정은 SRNet Ensemble.
    # - 위협이 없는 정상(CLEAN)은 귀속할 엔진이 없으므로 None(빈값).
    if aletheia_suspicious:
        return "HIGH", "SUSPICIOUS", "QUARANTINE", ENGINE_HYBRID
    if multicrop_enabled:
        if ensemble_high:
            return "HIGH", "SUSPICIOUS", "QUARANTINE", ENGINE_SRNET
        if ensemble_suspicious:
            return "MEDIUM", "SUSPICIOUS", "QUARANTINE", ENGINE_SRNET
        return "LOW", "CLEAN", "BYPASS", None

    if ensemble_high or stego_prob_pct >= high_threshold:
        return "HIGH", "SUSPICIOUS", "QUARANTINE", ENGINE_SRNET
    if ensemble_suspicious or stego_prob_pct >= medium_threshold:
        return "MEDIUM", "SUSPICIOUS", "QUARANTINE", ENGINE_SRNET
    return "LOW", "CLEAN", "BYPASS", None


def _aletheia_header_value(aletheia_result: dict) -> str:
    if aletheia_result.get("skipped"):
        return "SKIPPED"
    if not aletheia_result.get("available"):
        return "UNAVAILABLE"
    return "SUSPICIOUS" if aletheia_result.get("suspicious") else "CLEAN"


class ThresholdUpdateRequest(BaseModel):
    high_threshold: float
    medium_threshold: float


# ─────────────────────────────────────────────────
# 정책 관리: 탐지 임계값 설정
# ─────────────────────────────────────────────────
@app.get("/policy/threshold")
def get_threshold():
    high_threshold, medium_threshold = get_detection_thresholds()
    return {"high_threshold": high_threshold, "medium_threshold": medium_threshold}


@app.put("/policy/threshold")
def update_threshold(payload: ThresholdUpdateRequest):
    if not (0.0 <= payload.medium_threshold < payload.high_threshold <= 100.0):
        raise HTTPException(
            status_code=400,
            detail="임계값은 0 <= medium_threshold < high_threshold <= 100 조건을 만족해야 합니다.",
        )
    set_detection_thresholds(payload.high_threshold, payload.medium_threshold)
    return {"high_threshold": payload.high_threshold, "medium_threshold": payload.medium_threshold}


@app.get("/")
def read_root():
    return {
        "ai_model": "SRNet Ensemble (Max Router)",
        "loaded_models": [item["name"] for item in ensemble_models],
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

def _extract_file_id_from_stored_path(stored_path: str | None) -> str | None:
    if not stored_path:
        return None

    filename = os.path.basename(stored_path.replace("\\", "/"))
    if "_" not in filename:
        return None

    prefix = filename.split("_", 1)[0].strip()
    return prefix or None


def _fetch_mail_attachment_meta() -> tuple[dict[str, dict], list[dict]]:
    if not os.path.exists(MAIL_DB_PATH):
        return {}, []

    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            a.id AS attachment_id,
            a.mail_id,
            a.original_file_name,
            a.stored_path,
            a.file_size,
            a.mime_type,
            a.created_at AS attachment_created_at,
            m.sender_id,
            m.parent_mail_id,
            m.subject,
            m.body,
            m.status AS mail_status,
            m.sent_at AS mail_sent_at,
            m.created_at AS mail_created_at,
            mb.type AS mailbox_type,
            owner.email AS mailbox_owner_email,
            owner.username AS mailbox_owner_name,
            sender.email AS sender_email,
            sender.username AS sender_name
        FROM mail_attachment a
        JOIN mail m ON m.id = a.mail_id
        JOIN mailbox mb ON mb.id = m.mailbox_id
        LEFT JOIN employee owner ON owner.id = mb.employee_id
        LEFT JOIN employee sender ON sender.id = m.sender_id
        WHERE COALESCE(m.b_deleted, 'N') = 'N'
        ORDER BY COALESCE(a.created_at, m.sent_at, m.created_at) DESC, a.id DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT
            m.sender_id,
            m.parent_mail_id,
            m.subject,
            m.body,
            m.sent_at AS mail_sent_at,
            owner.email AS recipient_email
        FROM mail m
        JOIN mailbox mb ON mb.id = m.mailbox_id
        LEFT JOIN employee owner ON owner.id = mb.employee_id
        WHERE COALESCE(m.b_deleted, 'N') = 'N'
          AND UPPER(COALESCE(mb.type, '')) = 'INBOX'
    """)
    inbox_rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    inbox_recipients = {}
    for row in inbox_rows:
        key = (
            row.get("sender_id"),
            row.get("parent_mail_id"),
            row.get("subject"),
            row.get("body"),
            row.get("mail_sent_at"),
        )
        inbox_recipients[key] = row.get("mailbox_owner_email")

    by_file_id: dict[str, dict] = {}
    synthetic_logs: list[dict] = []
    seen_file_ids = set()

    for row in rows:
        file_id = _extract_file_id_from_stored_path(row.get("stored_path"))
        key = (
            row.get("sender_id"),
            row.get("parent_mail_id"),
            row.get("subject"),
            row.get("body"),
            row.get("mail_sent_at"),
        )
        mailbox_type = str(row.get("mailbox_type") or "").upper()
        recipient_email = row.get("mailbox_owner_email") if mailbox_type == "INBOX" else inbox_recipients.get(key)
        if not recipient_email and mailbox_type == "SENT":
            recipient_email = row.get("mailbox_owner_email")

        meta = {
            "file_id": file_id,
            "mail_id": row.get("mail_id"),
            "attachment_id": row.get("attachment_id"),
            "mail_subject": row.get("subject"),
            "mail_status": row.get("mail_status"),
            "mailbox_type": mailbox_type,
            "mail_sent_at": row.get("mail_sent_at"),
            "mail_created_at": row.get("mail_created_at"),
            "attachment_created_at": row.get("attachment_created_at"),
            "attachment_file_size": row.get("file_size"),
            "attachment_mime_type": row.get("mime_type"),
            "stored_path": row.get("stored_path"),
            "sender_email": row.get("sender_email"),
            "recipient_email": recipient_email,
        }

        if file_id and (file_id not in by_file_id or mailbox_type == "SENT"):
            by_file_id[file_id] = meta

        if file_id in seen_file_ids:
            continue
        seen_file_ids.add(file_id)

        synthetic_logs.append({
            "timestamp": row.get("attachment_created_at") or row.get("mail_sent_at") or row.get("mail_created_at"),
            "direction": "OUTBOUND" if mailbox_type == "SENT" else "INBOUND",
            "original_name": row.get("original_file_name"),
            "stego_probability": None,
            "risk_level": "UNKNOWN",
            "verdict": "UNSCANNED",
            "action": "MAIL_ATTACHMENT",
            **meta,
            "source": "mail",
        })

    return by_file_id, synthetic_logs


@app.get("/audit")
def get_audit():
    mail_meta_by_file_id, mail_attachment_logs = _fetch_mail_attachment_meta()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            timestamp,
            direction,
            original_name,
            stego_probability,
            risk_level,
            verdict,
            action,
            file_id,
            sender_email,
            recipient_email,
            detection_engine
        FROM audit_logs
        ORDER BY timestamp ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    logs = []
    audit_file_ids = set()
    for row in rows:
        log = dict(row)
        file_id = log.get("file_id")
        if file_id:
            audit_file_ids.add(file_id)
            meta = mail_meta_by_file_id.get(file_id)
            if not meta:
                meta = next(
                    (value for key, value in mail_meta_by_file_id.items() if file_id.startswith(f"{key}_")),
                    None,
                )
            if meta:
                log.update({k: v for k, v in meta.items() if v is not None})
                log["source"] = "audit_mail"
            else:
                log["source"] = "audit"
        else:
            log["source"] = "audit"
        logs.append(log)

    for mail_log in mail_attachment_logs:
        file_id = mail_log.get("file_id")
        if file_id and file_id in audit_file_ids:
            continue
        logs.append(mail_log)

    logs.sort(key=lambda log: log.get("timestamp") or log.get("mail_sent_at") or "")
    suspicious_count = sum(1 for log in logs if log["verdict"] == "SUSPICIOUS")
    
    return {
        "total_count": len(logs),
        "suspicious_count": suspicious_count,
        "mail_attachment_count": len(mail_attachment_logs),
        "logs": logs
    }

def _get_extension(filename: str | None) -> str:
    if not filename:
        return "unknown"

    name = filename.split("::")[-1].strip()
    ext = os.path.splitext(name)[1].lower().replace(".", "")

    return ext if ext else "unknown"


def _normalize_action(action: str | None) -> str:
    return str(action or "").upper()


def _is_policy_blocked(log: dict) -> bool:
    action = _normalize_action(log.get("action"))
    return "POLICY" in action or action == "POLICY_SANITIZED"


def _is_quarantined(log: dict) -> bool:
    action = _normalize_action(log.get("action"))
    return "QUARANTINE" in action or _is_policy_blocked(log)


def _is_delivered(log: dict) -> bool:
    action = _normalize_action(log.get("action"))
    verdict = str(log.get("verdict") or "").upper()

    if _is_quarantined(log):
        return False

    return (
            "BYPASS" in action
            or action == "MAIL_ATTACHMENT"
            or verdict == "CLEAN"
    )


def _get_cdr_logs() -> list[dict]:
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            file_id,
            file_name,
            stego_probability,
            decoded_message,
            rescan_probability,
            processed_at,
            risk_level,
            action,
            original_kb,
            sanitized_kb,
            avg_pixel_diff
        FROM cdr_logs
        ORDER BY processed_at DESC
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def _safe_rate(part: int | float, total: int | float) -> float:
    if not total:
        return 0.0
    return round((part / total) * 100, 1)


def _parse_report_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _get_report_time(log: dict) -> datetime | None:
    return _parse_report_date(
        log.get("timestamp")
        or log.get("attachment_created_at")
        or log.get("mail_sent_at")
        or log.get("mail_created_at")
        or log.get("processed_at")
    )


def _report_bucket(dt: datetime, period: str) -> str:
    if period == "month":
        return dt.strftime("%Y-%m")
    if period == "week":
        iso_year, iso_week, _ = dt.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    return dt.strftime("%Y-%m-%d")


def _risk_score(log: dict) -> float:
    probability = log.get("stego_probability")
    try:
        if probability is not None:
            return float(probability)
    except (TypeError, ValueError):
        pass

    return {
        "HIGH": 90.0,
        "MEDIUM": 55.0,
        "LOW": 15.0,
        "UNKNOWN": 0.0,
    }.get(str(log.get("risk_level") or "UNKNOWN").upper(), 0.0)


def _filter_report_logs(logs: list[dict], start_date: str | None, end_date: str | None) -> list[dict]:
    start = _parse_report_date(start_date)
    end = _parse_report_date(end_date)
    if end:
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

    filtered = []
    for log in logs:
        dt = _get_report_time(log)
        if not dt:
            continue
        if start and dt < start:
            continue
        if end and dt > end:
            continue
        filtered.append({**log, "_report_dt": dt})
    return filtered


def _empty_daily_row(bucket: str) -> dict:
    return {
        "date": bucket,
        "total_count": 0,
        "clean_count": 0,
        "suspicious_count": 0,
        "unscanned_count": 0,
        "cdr_count": 0,
        "policy_count": 0,
        "quarantine_count": 0,
        "bypass_count": 0,
        "mail_count": 0,
        "other_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "unknown_count": 0,
        "_risk_sum": 0.0,
        "max_risk_score": 0.0,
    }


def _apply_report_counts(row: dict, log: dict) -> None:
    verdict = str(log.get("verdict") or "").upper()
    risk_level = str(log.get("risk_level") or "UNKNOWN").upper()
    action = _normalize_action(log.get("action"))
    score = _risk_score(log)

    row["total_count"] += 1
    row["_risk_sum"] += score
    row["max_risk_score"] = max(row["max_risk_score"], score)

    if verdict == "CLEAN":
        row["clean_count"] += 1
    elif verdict == "SUSPICIOUS":
        row["suspicious_count"] += 1
    elif verdict == "UNSCANNED":
        row["unscanned_count"] += 1

    if risk_level == "HIGH":
        row["high_count"] += 1
    elif risk_level == "MEDIUM":
        row["medium_count"] += 1
    elif risk_level == "LOW":
        row["low_count"] += 1
    else:
        row["unknown_count"] += 1

    if "POLICY" in action or "BLOCK" in action:
        row["policy_count"] += 1
    elif "QUARANTINE" in action:
        row["quarantine_count"] += 1
    elif "SANITIZED" in action or "CDR" in action:
        row["cdr_count"] += 1
    elif action in ("BYPASS", "PASSED"):
        row["bypass_count"] += 1
    elif action == "MAIL_ATTACHMENT":
        row["mail_count"] += 1
    else:
        row["other_count"] += 1


def _finalize_report_row(row: dict) -> dict:
    total = row["total_count"]
    row["avg_risk_score"] = round(row["_risk_sum"] / total, 1) if total else 0.0
    row["max_risk_score"] = round(row["max_risk_score"], 1)
    row.pop("_risk_sum", None)
    return row


def _set_no_cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


@app.get("/reports/daily-detections")
def get_daily_detection_report(response: Response, start_date: str | None = None, end_date: str | None = None, period: str = "day"):
    _set_no_cache_headers(response)
    period = period if period in ("day", "week", "month") else "day"
    rows_by_bucket: dict[str, dict] = {}

    for log in _filter_report_logs(get_audit().get("logs", []), start_date, end_date):
        bucket = _report_bucket(log["_report_dt"], period)
        row = rows_by_bucket.setdefault(bucket, _empty_daily_row(bucket))
        _apply_report_counts(row, log)

    rows = [_finalize_report_row(row) for _, row in sorted(rows_by_bucket.items())]
    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "rows": rows,
    }


@app.get("/reports/risk-trend")
def get_risk_trend_report(response: Response, start_date: str | None = None, end_date: str | None = None, period: str = "day"):
    _set_no_cache_headers(response)
    period = period if period in ("day", "week", "month") else "day"
    rows_by_bucket: dict[str, dict] = {}

    for log in _filter_report_logs(get_audit().get("logs", []), start_date, end_date):
        bucket = _report_bucket(log["_report_dt"], period)
        row = rows_by_bucket.setdefault(bucket, _empty_daily_row(bucket))
        _apply_report_counts(row, log)

    rows = []
    for _, row in sorted(rows_by_bucket.items()):
        finalized = _finalize_report_row(row)
        rows.append({
            "bucket": finalized["date"],
            "score": finalized["avg_risk_score"],
            "avg_score": finalized["avg_risk_score"],
            "max_score": finalized["max_risk_score"],
            "total_count": finalized["total_count"],
            "suspicious_count": finalized["suspicious_count"],
            "high_count": finalized["high_count"],
            "medium_count": finalized["medium_count"],
            "low_count": finalized["low_count"],
            "cdr_count": finalized["cdr_count"],
            "policy_count": finalized["policy_count"],
        })

    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "rows": rows,
    }


@app.get("/reports/file-types")
def get_file_type_report(response: Response, start_date: str | None = None, end_date: str | None = None):
    _set_no_cache_headers(response)
    rows_by_key: dict[tuple[str, str], dict] = {}

    for log in _filter_report_logs(get_audit().get("logs", []), start_date, end_date):
        extension = _get_extension(log.get("original_name"))
        mime_type = log.get("attachment_mime_type") or "unknown"
        key = (extension, mime_type)
        row = rows_by_key.setdefault(key, {
            "extension": extension,
            "mime_type": mime_type,
            **_empty_daily_row(extension),
        })
        _apply_report_counts(row, log)

    rows = []
    for _, row in sorted(rows_by_key.items(), key=lambda item: item[1]["total_count"], reverse=True):
        finalized = _finalize_report_row(row)
        finalized.pop("date", None)
        rows.append(finalized)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "rows": rows,
    }


@app.get("/dashboard/threat-overview")
def get_threat_overview():
    audit_data = get_audit()
    logs = audit_data.get("logs", [])
    cdr_logs = _get_cdr_logs()

    total_files = len(logs)
    scanned_logs = [
        log for log in logs
        if str(log.get("verdict") or "").upper() not in ("UNSCANNED", "")
    ]

    scanned_count = len(scanned_logs)

    suspicious_logs = [
        log for log in logs
        if str(log.get("verdict") or "").upper() == "SUSPICIOUS"
    ]

    clean_logs = [
        log for log in logs
        if str(log.get("verdict") or "").upper() == "CLEAN"
    ]

    unscanned_logs = [
        log for log in logs
        if str(log.get("verdict") or "").upper() == "UNSCANNED"
    ]

    quarantine_logs = [log for log in logs if _is_quarantined(log)]
    policy_logs = [log for log in logs if _is_policy_blocked(log)]
    delivered_logs = [log for log in logs if _is_delivered(log)]

    risk_distribution = Counter(
        str(log.get("risk_level") or "UNKNOWN").upper()
        for log in logs
    )

    direction_distribution = Counter(
        str(log.get("direction") or "UNKNOWN").upper()
        for log in logs
    )

    action_distribution = Counter(
        str(log.get("action") or "UNKNOWN").upper()
        for log in logs
    )

    extension_distribution = Counter(
        _get_extension(log.get("original_name"))
        for log in logs
    )

    latest_logs = sorted(
        logs,
        key=lambda log: log.get("timestamp") or log.get("mail_sent_at") or "",
        reverse=True
    )[:10]

    latest_cdr = sorted(
        cdr_logs,
        key=lambda log: log.get("processed_at") or "",
        reverse=True
    )[:8]

    high_threshold, medium_threshold = get_detection_thresholds()

    def latest_time(items, *fields):
        latest = None

        for item in items:
            for field in fields:
                value = item.get(field)
                if not value:
                    continue

                if latest is None or value > latest:
                    latest = value

                break

        return latest

    now_iso = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()

    last_scan_at = latest_time(
        scanned_logs,
        "timestamp",
        "mail_sent_at",
    )

    last_cdr_at = latest_time(
        cdr_logs,
        "processed_at",
    )

    last_quarantine_at = latest_time(
        quarantine_logs,
        "timestamp",
        "mail_sent_at",
    )

    last_policy_at = latest_time(
        policy_logs,
        "timestamp",
        "mail_sent_at",
    )

    mail_logs = [
        log for log in logs
        if log.get("source") in ("mail", "audit_mail")
           or log.get("mail_sent_at")
           or log.get("mail_created_at")
           or log.get("attachment_created_at")
    ]

    last_mail_at = latest_time(
        mail_logs,
        "mail_sent_at",
        "attachment_created_at",
        "mail_created_at",
        "timestamp",
    )

    avg_before = None
    avg_after = None
    avg_reduction = None

    valid_cdr = [
        log for log in cdr_logs
        if log.get("stego_probability") is not None
           and log.get("rescan_probability") is not None
    ]

    if valid_cdr:
        avg_before = round(
            sum(float(log["stego_probability"]) for log in valid_cdr) / len(valid_cdr),
            1
        )
        avg_after = round(
            sum(float(log["rescan_probability"]) for log in valid_cdr) / len(valid_cdr),
            1
        )
        avg_reduction = round(
            sum(
                max(
                    0,
                    1 - (
                            float(log["rescan_probability"])
                            / max(float(log["stego_probability"]), 0.1)
                    )
                )
                for log in valid_cdr
            ) / len(valid_cdr) * 100,
            1
        )

    system_status = [
        {
            "name": "API Gateway",
            "type": "SERVER",
            "status": "RUNNING",
            "detail": "FastAPI gateway online",
            "last_activity_label": "Last Request",
            "last_activity_at": now_iso,
        },
        {
            "name": "AI Engine",
            "type": "MES",
            "status": "RUNNING" if ensemble_models else "DEGRADED",
            "detail": f"{len(ensemble_models)} model(s) loaded",
            "last_activity_label": "Last Scan",
            "last_activity_at": last_scan_at,
        },
        {
            "name": "CDR Module",
            "type": "MES",
            "status": "RUNNING" if os.path.exists(SANITIZED_DIR) else "DEGRADED",
            "detail": "sanitized storage ready" if os.path.exists(SANITIZED_DIR) else "sanitized storage missing",
            "last_activity_label": "Last CDR",
            "last_activity_at": last_cdr_at,
        },
        {
            "name": "Quarantine Storage",
            "type": "WMS",
            "status": "RUNNING" if os.path.exists(QUARANTINE_DIR) else "DEGRADED",
            "detail": "quarantine storage ready" if os.path.exists(QUARANTINE_DIR) else "quarantine storage missing",
            "last_activity_label": "Last Quarantine",
            "last_activity_at": last_quarantine_at,
        },
        {
            "name": "Policy Engine",
            "type": "ERP",
            "status": "RUNNING",
            "detail": f"HIGH {high_threshold}% / MEDIUM {medium_threshold}%",
            "last_activity_label": "Last Policy Hit",
            "last_activity_at": last_policy_at,
        },
        {
            "name": "Mail Gateway",
            "type": "WMS",
            "status": "RUNNING" if os.path.exists(MAIL_DB_PATH) else "DEGRADED",
            "detail": "mail DB connected" if os.path.exists(MAIL_DB_PATH) else "mail DB missing",
            "last_activity_label": "Last Mail",
            "last_activity_at": last_mail_at,
        },
    ]

    return {
        "generated_at": now_iso,

        "summary": {
            "total_files": total_files,
            "scanned_files": scanned_count,
            "suspicious_files": len(suspicious_logs),
            "clean_files": len(clean_logs),
            "unscanned_files": len(unscanned_logs),
            "cdr_processed": len(cdr_logs),
            "quarantined": len(quarantine_logs),
            "policy_blocked": len(policy_logs),
            "delivered": len(delivered_logs),
            "threat_rate": _safe_rate(len(suspicious_logs), scanned_count),
            "delivery_rate": _safe_rate(len(delivered_logs), total_files),
        },

        "mes_process": {
            "received": total_files,
            "ai_scanned": scanned_count,
            "judged": len(clean_logs) + len(suspicious_logs),
            "cdr_processed": len(cdr_logs),
            "quarantined": len(quarantine_logs),
            "delivered": len(delivered_logs),
        },

        "wms_inventory": {
            "inbound_files": direction_distribution.get("INBOUND", 0),
            "outbound_files": direction_distribution.get("OUTBOUND", 0),
            "quarantine_storage": len(quarantine_logs),
            "sanitized_storage": len(cdr_logs),
            "mail_unscanned": len(unscanned_logs),
            "delivered_files": len(delivered_logs),
        },

        "erp_metrics": {
            "threat_rate": _safe_rate(len(suspicious_logs), scanned_count),
            "clean_rate": _safe_rate(len(clean_logs), scanned_count),
            "quarantine_rate": _safe_rate(len(quarantine_logs), total_files),
            "policy_violation_rate": _safe_rate(len(policy_logs), total_files),
            "cdr_conversion_rate": _safe_rate(len(cdr_logs), max(len(suspicious_logs), 1)),
            "avg_before_risk": avg_before,
            "avg_after_risk": avg_after,
            "avg_risk_reduction": avg_reduction,
        },

        "risk_distribution": dict(risk_distribution),
        "direction_distribution": dict(direction_distribution),
        "action_distribution": dict(action_distribution),
        "extension_distribution": dict(extension_distribution),

        "system_status": system_status,
        "recent_events": latest_logs,
        "recent_cdr": latest_cdr,
    }

def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def _get_dashboard_visit_stats(cursor) -> dict:
    import time

    now_ts = time.time()
    active_cutoff = now_ts - 60

    cursor.execute(
        "DELETE FROM dashboard_active_visitors WHERE last_seen < ?",
        (active_cutoff,)
    )

    cursor.execute("SELECT total_views FROM dashboard_metrics WHERE id = 1")
    row = cursor.fetchone()
    total_views = row[0] if row else 0

    cursor.execute("SELECT COUNT(*) FROM dashboard_active_visitors")
    current_visitors = cursor.fetchone()[0]

    return {
        "total_views": total_views,
        "current_visitors": current_visitors,
        "active_window_seconds": 60,
    }


@app.post("/dashboard/threat-overview/view")
def record_threat_overview_view(request: Request):
    import time

    client_ip = _get_client_ip(request)
    now_ts = time.time()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 한 IP라도 새로고침/재조회할 때마다 무한 증가 가능
    cursor.execute("""
        UPDATE dashboard_metrics
        SET total_views = total_views + 1
        WHERE id = 1
    """)

    # 현재 방문자 수는 최근 60초 안에 살아있는 IP 기준
    cursor.execute("""
        INSERT INTO dashboard_active_visitors (client_ip, last_seen)
        VALUES (?, ?)
        ON CONFLICT(client_ip)
        DO UPDATE SET last_seen = excluded.last_seen
    """, (client_ip, now_ts))

    stats = _get_dashboard_visit_stats(cursor)

    conn.commit()
    conn.close()

    return stats


@app.post("/dashboard/threat-overview/heartbeat")
def heartbeat_threat_overview(request: Request):
    import time

    client_ip = _get_client_ip(request)
    now_ts = time.time()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # heartbeat는 조회수 증가 X
    # 현재 방문자 유지용
    cursor.execute("""
        INSERT INTO dashboard_active_visitors (client_ip, last_seen)
        VALUES (?, ?)
        ON CONFLICT(client_ip)
        DO UPDATE SET last_seen = excluded.last_seen
    """, (client_ip, now_ts))

    stats = _get_dashboard_visit_stats(cursor)

    conn.commit()
    conn.close()

    return stats

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

DANGEROUS_ATTACHMENT_EXTENSIONS = {
    ".7z",
    ".ace",
    ".app",
    ".bat",
    ".chm",
    ".cmd",
    ".com",
    ".cpl",
    ".crt",
    ".deb",
    ".dll",
    ".dmg",
    ".exe",
    ".gadget",
    ".gzi",
    ".hta",
    ".img",
    ".inf",
    ".ins",
    ".iso",
    ".jar",
    ".jnlp",
    ".js",
    ".jse",
    ".lnk",
    ".mde",
    ".msc",
    ".msi",
    ".msp",
    ".mst",
    ".pif",
    ".ps1",
    ".ps1xml",
    ".ps2",
    ".ps2xml",
    ".psc1",
    ".psc2",
    ".pub",
    ".py",
    ".pyc",
    ".pyo",
    ".pyw",
    ".rar",
    ".reg",
    ".rpm",
    ".scr",
    ".sct",
    ".sh",
    ".svg",
    ".swf",
    ".tar",
    ".vbe",
    ".vbs",
    ".xll",
    ".wsf",
    ".wsh",
    ".xz",
    ".z",
}

MACRO_DOCUMENT_EXTENSIONS = {
    ".docm",
    ".dotm",
    ".potm",
    ".ppam",
    ".ppsm",
    ".pptm",
    ".sldm",
    ".xlsb",
    ".xlsm",
    ".xltm",
}

DECOY_DOCUMENT_EXTENSIONS = {
    ".doc",
    ".docx",
    ".hwp",
    ".hwpx",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}

SOCIAL_ENGINEERING_KEYWORDS = (
    "resume",
    "cv",
    "invoice",
    "contract",
    "quotation",
    "estimate",
    "application",
    "이력서",
    "입사지원",
    "견적",
    "견적서",
    "계약",
    "계약서",
    "청구서",
    "개인정보",
)


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


def _attachment_policy_findings(filename: str, content_type: str, contents: bytes) -> list[str]:
    """Return policy findings for non-image attachment risk signals."""
    safe_name = os.path.basename(filename or "attachment")
    lower_name = safe_name.lower()
    suffixes = [suffix.lower() for suffix in PurePosixPath(lower_name).suffixes]
    findings = []

    if suffixes and suffixes[-1] in DANGEROUS_ATTACHMENT_EXTENSIONS:
        findings.append(f"dangerous_extension:{suffixes[-1]}")

    if suffixes and suffixes[-1] in MACRO_DOCUMENT_EXTENSIONS:
        findings.append(f"macro_document:{suffixes[-1]}")

    if len(suffixes) >= 2 and suffixes[-1] in DANGEROUS_ATTACHMENT_EXTENSIONS:
        if any(suffix in DECOY_DOCUMENT_EXTENSIONS for suffix in suffixes[:-1]):
            findings.append("double_extension_decoy")

    if any(keyword in lower_name for keyword in SOCIAL_ENGINEERING_KEYWORDS):
        findings.append("social_engineering_filename")

    declared_type = (content_type or "").lower()
    if declared_type.startswith("image/") and imghdr.what(None, h=contents) is None:
        findings.append("mime_extension_mismatch")

    return findings


def _requires_policy_sanitization(findings: list[str]) -> bool:
    return any(
        finding.startswith("dangerous_extension:")
        or finding.startswith("macro_document:")
        or finding == "double_extension_decoy"
        or finding == "mime_extension_mismatch"
        for finding in findings
    )


def _write_policy_sanitized_notice(file_id: str, original_name: str, findings: list[str]) -> str:
    safe_name = _safe_disk_name(original_name) or "attachment"
    safe_stem = os.path.splitext(safe_name)[0] or "attachment"
    output_name = f"{file_id}_{safe_stem}_sanitized.txt"
    output_path = os.path.join(SANITIZED_DIR, output_name)

    notice = "\n".join([
        "/etc/friends Attachment Sanitization Notice",
        "",
        "The original attachment was replaced by policy-based sanitization.",
        "Reason(s):",
        *[f"- {finding}" for finding in findings],
        "",
        "The gateway does not deliver executable or script-like attachments.",
        "If this file is business-critical, contact the security administrator.",
    ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(notice)

    return output_path


def _find_sanitized_attachment_path(file_id: str, original_filename: str) -> str | None:
    safe_name = _safe_disk_name(original_filename)
    safe_name_no_ext = os.path.splitext(safe_name)[0]
    preferred = os.path.join(SANITIZED_DIR, f"{file_id}_{safe_name_no_ext}_sanitized.jpg")
    if os.path.exists(preferred):
        return preferred

    prefix = f"{file_id}_"
    suffix_prefix = f"{file_id}_{safe_name_no_ext}_sanitized."
    for filename in os.listdir(SANITIZED_DIR):
        if filename.startswith(suffix_prefix) or (filename.startswith(prefix) and "_sanitized." in filename):
            candidate = os.path.join(SANITIZED_DIR, filename)
            if os.path.isfile(candidate):
                return candidate

    return None


def _scan_policy_attachment_bytes(contents: bytes, display_name: str, content_type: str, direction: str, file_id: str, findings: list[str]):
    """Sanitize risky non-image attachments by replacing them with a safe notice file."""
    safe_name = _safe_disk_name(display_name) or "attachment"
    input_filename = f"{file_id}_{safe_name}"
    input_path = os.path.join(UPLOAD_DIR, input_filename)

    with open(input_path, "wb") as f:
        f.write(contents)

    output_path = _write_policy_sanitized_notice(file_id, display_name, findings)

    quarantine_path = os.path.join(QUARANTINE_DIR, input_filename)
    shutil.move(input_path, quarantine_path)

    try:
        os.chmod(quarantine_path, 0o440)
    except Exception:
        pass

    try:
        if S3_BUCKET:
            s3.upload_file(quarantine_path, S3_BUCKET, f"quarantine/{input_filename}")
            s3.upload_file(output_path, S3_BUCKET, f"sanitized/{os.path.basename(output_path)}")
    except Exception as e:
        print(f"S3 Upload Failed: {e}")

    _record_audit(
        direction=direction,
        original_name=display_name,
        stego_prob_pct=100.0,
        risk_level="HIGH",
        verdict="SUSPICIOUS",
        action="POLICY_SANITIZED",
        file_id=file_id,
        detection_engine=ENGINE_POLICY,
    )

    sanitized_download_name = f"{os.path.splitext(safe_name)[0]}_sanitized.txt"

    return {
        "original_name": display_name,
        "download_name": sanitized_download_name,
        "stego_probability": 100.0,
        "risk_level": "HIGH",
        "verdict": "SUSPICIOUS",
        "action": "POLICY_SANITIZED",
        "policy": {
            "findings": findings,
            "sanitized_replacement": True,
        },
        "sanitized_path": output_path,
    }


def _record_audit(
    direction: str,
    original_name: str,
    stego_prob_pct: float,
    risk_level: str,
    verdict: str,
    action: str,
    file_id: str | None = None,
    sender_email: str | None = None,
    recipient_email: str | None = None,
    detection_engine: str | None = None,
):

    """
    기존 audit_logs 테이블에 로그 저장.
    압축파일 내부 이미지 검사에서도 같은 로그 구조를 재사용한다.
    detection_engine: 위험 판정에 기여한 엔진 라벨. 정상 로그는 None(빈값).
    """
    timestamp_str = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs
        (timestamp, direction, original_name, stego_probability, risk_level, verdict, action, file_id, sender_email, recipient_email, detection_engine)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp_str,
        direction,
        original_name,
        round(stego_prob_pct, 1),
        risk_level,
        verdict,
        action,
        file_id,
        sender_email,
        recipient_email,
        detection_engine,
    ))
    conn.commit()
    conn.close()


def _attach_mail_participants_to_audit(file_ids: list[str], sender_email: str, recipient_email: str) -> None:
    if not file_ids:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for file_id in file_ids:
        cursor.execute("""
            UPDATE audit_logs
            SET sender_email = ?, recipient_email = ?
            WHERE file_id = ? OR file_id LIKE ?
        """, (
            sender_email,
            recipient_email,
            file_id,
            f"{file_id}_%",
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

    ensemble_result = _predict_ensemble_image(img, img_format)
    stego_prob_pct = ensemble_result["stego_prob_pct"]
    aletheia_result = _run_aletheia(input_path, img_format)
    high_threshold, medium_threshold = get_detection_thresholds()
    risk_level, verdict, action, detection_engine = _classify_scan(
        stego_prob_pct,
        aletheia_result,
        ensemble_result,
        high_threshold,
        medium_threshold,
    )

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

    logged_stego_prob_pct = stego_prob_pct
    if (
        verdict == "CLEAN"
        and ensemble_result.get("multicrop", {}).get("enabled")
    ):
        logged_stego_prob_pct = min(stego_prob_pct, max(0.0, medium_threshold - 0.1))

    _record_audit(
        direction=direction,
        original_name=display_name,
        stego_prob_pct=logged_stego_prob_pct,
        risk_level=risk_level,
        verdict=verdict,
        action=action,
        file_id=file_id,
        detection_engine=detection_engine,
    )
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cdr_logs
        (file_id, file_name, stego_probability, decoded_message, processed_at,
         risk_level, action, original_kb, sanitized_kb, avg_pixel_diff)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id,
        display_name,
        round(logged_stego_prob_pct, 1),
        None,
        datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        risk_level,
        action,
        cdr_info.get("original_kb"),
        cdr_info.get("sanitized_kb"),
        cdr_info.get("avg_pixel_diff"),
    ))
    conn.commit()
    conn.close()


    return {
        "original_name": display_name,
        "stego_probability": round(logged_stego_prob_pct, 1),
        "risk_level": risk_level,
        "verdict": verdict,
        "action": action,
        "detection_engine": detection_engine,
        "aletheia": aletheia_result,
        "ensemble": {
            "route_model": ensemble_result.get("route_model"),
            "route_display_name": ensemble_result.get("route_display_name"),
            "model_scores": ensemble_result.get("model_scores", []),
            "multicrop": ensemble_result.get("multicrop", {}),
        },
        "sanitized_path": output_path,
        "cdr": cdr_info,
    }


def _scan_archive_bytes(contents: bytes, archive_name: str, direction: str, file_id: str):
    """
    ZIP 내부 이미지를 전부 검사하고,
    CDR 처리된 이미지들만 모아서 sanitized ZIP으로 저장한다.
    """
    if len(contents) > MAX_ARCHIVE_SIZE:
        raise HTTPException(status_code=413, detail="Archive too large")

    if not zipfile.is_zipfile(io.BytesIO(contents)):
        raise HTTPException(status_code=400, detail="Unsupported archive format. ZIP only.")

    result_zip_name = f"{file_id}_{_safe_disk_name(os.path.splitext(archive_name)[0] or 'archive')}_sanitized.zip"
    result_zip_path = os.path.join(SANITIZED_DIR, result_zip_name)

    results = []
    suspicious_count = 0
    policy_removed_count = 0
    archive_policy_findings = []
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

            else:
                member_findings = _attachment_policy_findings(
                    member_name,
                    "application/octet-stream",
                    raw,
                )

                if member_findings:
                    policy_removed_count += 1
                    archive_policy_findings.extend(member_findings)
                    _record_audit(
                        direction=direction,
                        original_name=f"{archive_name}::{member_name}",
                        stego_prob_pct=100.0,
                        risk_level="HIGH",
                        verdict="SUSPICIOUS",
                        action="POLICY_SANITIZED",
                        file_id=f"{file_id}_policy_{policy_removed_count}",
                        detection_engine=ENGINE_POLICY,
                    )
                    continue

                if ALLOW_NON_IMAGE_IN_ARCHIVE:
                    # 기본값 false.
                    # 보안 게이트웨이 관점에서는 이미지 외 파일은 드롭하는 편이 안전하다.
                    zout.writestr(member_name, raw)
                else:
                    policy_removed_count += 1

    if image_count == 0:
        raise HTTPException(status_code=400, detail="No supported images found inside archive")

    has_policy_findings = bool(archive_policy_findings)
    overall_verdict = "SUSPICIOUS" if suspicious_count or has_policy_findings else "CLEAN"

    overall_risk = (
        "HIGH"
        if has_policy_findings or any(r["risk_level"] == "HIGH" for r in results)
        else ("MEDIUM" if suspicious_count else "LOW")
    )

    overall_action = (
        "POLICY_SANITIZED"
        if has_policy_findings
        else ("QUARANTINE" if suspicious_count else "BYPASS")
    )
    max_prob = max(r["stego_probability"] for r in results)

    # 요약 행 엔진 귀속: 내부 이미지별 엔진 + 정책 위반 여부를 취합.
    # 서로 다른 엔진이 함께 기여했으면 Hybrid Detection, 정상만 있으면 빈값(None).
    summary_engines = {r.get("detection_engine") for r in results if r.get("detection_engine")}
    if has_policy_findings:
        summary_engines.add(ENGINE_POLICY)
    if len(summary_engines) > 1:
        overall_engine = ENGINE_HYBRID
    elif summary_engines:
        overall_engine = next(iter(summary_engines))
    else:
        overall_engine = None

    # 압축파일 전체 요약 로그 1개 추가.
    # 내부 이미지별 로그는 _scan_image_bytes()에서 이미 저장됨.
    _record_audit(
        direction=direction,
        original_name=archive_name,
        stego_prob_pct=max_prob,
        risk_level=overall_risk,
        verdict=overall_verdict,
        action=f"ARCHIVE_{overall_action}",
        file_id=file_id,
        detection_engine=overall_engine,
    )

    return {
        "sanitized_path": result_zip_path,
        "download_name": result_zip_name,
        "verdict": overall_verdict,
        "risk_level": overall_risk,
        "stego_probability": max_prob,
        "image_count": image_count,
        "suspicious_count": suspicious_count,
        "policy_removed_count": policy_removed_count,
        "policy_findings": sorted(set(archive_policy_findings)),
    }

# ─────────────────────────────────────────────────
# LSB 디코더
# RGB 채널의 최하위 비트를 읽어 NULL 문자까지 문자열 복원
# CDR 전 원본 이미지의 은닉 메시지 검증 용도
# ─────────────────────────────────────────────────
def _decode_lsb_message(image_path: str):
    from PIL import Image

    try:
        img = Image.open(image_path).convert("RGB")
        bits = []

        for r, g, b in img.getdata():
            bits.extend([str(r & 1), str(g & 1), str(b & 1)])

        chars = []
        for i in range(0, len(bits), 8):
            byte = bits[i:i + 8]
            if len(byte) < 8:
                break

            ch = chr(int("".join(byte), 2))

            if ch == "\x00":
                break

            chars.append(ch)

            if len(chars) >= 500:
                break

        message = "".join(chars).strip()

        if not message:
            return None

        printable_count = sum(1 for c in message if c in string.printable and c not in "\x0b\x0c")
        printable_ratio = printable_count / max(len(message), 1)

        if printable_ratio < 0.85:
            return None

        clean_message = "".join(
            c for c in message
            if c in string.printable and c not in "\x0b\x0c"
        ).strip()

        if len(clean_message) < 3:
            return None

        return clean_message[:500]

    except Exception:
        return None

# ─────────────────────────────────────────────────
# DCT 디코더
# DCT 중간주파수 계수의 부호를 읽어
# NULL 문자까지 문자열 복원
# DCT 스테가노 이미지 검증 용도
# ─────────────────────────────────────────────────
def _decode_dct_message(image_path: str):
    import cv2
    import numpy as np
    from PIL import Image

    MESSAGE_FREQ = (3, 2)

    try:
        img = Image.open(image_path).convert("RGB")
        rgb = np.array(img)

        ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
        y = ycrcb[:, :, 0]

        h, w = y.shape
        h8 = h - (h % 8)
        w8 = w - (w % 8)

        bits = []

        for yy in range(0, h8, 8):
            for xx in range(0, w8, 8):
                block = y[yy:yy + 8, xx:xx + 8] - 128.0
                dct = cv2.dct(block)

                u, v = MESSAGE_FREQ
                bits.append(1 if dct[u, v] >= 0 else 0)

        chars = []

        for i in range(0, len(bits), 8):
            byte = bits[i:i + 8]

            if len(byte) < 8:
                break

            ch = chr(int("".join(map(str, byte)), 2))

            if ch == "\x00":
                break

            chars.append(ch)

            if len(chars) >= 500:
                break

        message = "".join(chars).strip()

        return message if message else None

    except Exception:
        return None

# ─────────────────────────────────────────────────
# DWT-Haar 디코더
# 2x2 Haar HH 계수의 부호를 읽어
# NULL 문자까지 문자열 복원
# DWT 스테가노 이미지 검증 용도
# ─────────────────────────────────────────────────
def _decode_dwt_message(image_path: str):
    from PIL import Image
    import numpy as np
    import string

    try:
        img = Image.open(image_path).convert("RGB")
        rgb = np.array(img).astype(np.float32)

        # 생성 코드에서 R,G,B 전체에 동일한 2x2 패턴을 넣기 때문에
        # 복원은 R 채널만 읽어도 된다.
        y = rgb[:, :, 0]

        h, w = y.shape
        h2 = h - (h % 2)
        w2 = w - (w % 2)
        y = y[:h2, :w2]

        a = y[0::2, 0::2]
        b = y[0::2, 1::2]
        c = y[1::2, 0::2]
        d = y[1::2, 1::2]

        # Haar HH 계수
        hh = (a - b - c + d) * 0.25

        bits = []
        for value in hh.reshape(-1):
            bits.append(1 if value >= 0 else 0)

        chars = []

        for i in range(0, len(bits), 8):
            byte = bits[i:i + 8]

            if len(byte) < 8:
                break

            value = int("".join(map(str, byte)), 2)

            if value == 0:
                break

            chars.append(chr(value))

            if len(chars) >= 500:
                break

        message = "".join(chars).strip()

        if not message:
            return None

        printable_count = sum(
            1 for c in message
            if c in string.printable and c not in "\x0b\x0c"
        )

        printable_ratio = printable_count / max(len(message), 1)

        if printable_ratio < 0.85:
            return None

        clean_message = "".join(
            c for c in message
            if c in string.printable and c not in "\x0b\x0c"
        ).strip()

        if len(clean_message) < 3:
            return None

        return clean_message[:500]

    except Exception as exc:
        print(f"[DWT DECODE ERROR] {exc}")
        return None

    
@app.post("/scan")
async def scan_and_sanitize(
    file: UploadFile = File(...),
    direction: str = Form("INBOUND")
):
    file_id = str(uuid.uuid4())[:8]
    contents = await file.read()
    # ZIP 압축파일이면 내부 이미지를 개별 스캔 + CDR 후 sanitized zip 메타데이터를 반환
    content_type = (file.content_type or "").lower()
    filename_lower = (file.filename or "").lower()
    original_filename = file.filename or "stream"

    policy_findings = _attachment_policy_findings(original_filename, content_type, contents)
    if _requires_policy_sanitization(policy_findings):
        result = _scan_policy_attachment_bytes(
            contents=contents,
            display_name=original_filename,
            content_type=file.content_type or "application/octet-stream",
            direction=direction,
            file_id=file_id,
            findings=policy_findings,
        )
        return {
            "file_id": file_id,
            "original_filename": result["download_name"],
            "file_size": os.path.getsize(result["sanitized_path"]),
            "mime_type": "text/plain",
            "verdict": result["verdict"],
            "risk_level": result["risk_level"],
            "stego_probability": result["stego_probability"],
            "model": "policy_engine",
            "model_scores": [],
            "aletheia": "SKIPPED",
            "policy": result["policy"],
            "sanitized_path": result["sanitized_path"],
        }

    is_zip_payload = zipfile.is_zipfile(io.BytesIO(contents))

    if filename_lower.endswith(".zip") or content_type in ARCHIVE_MIMES or is_zip_payload:
      if not is_zip_payload:
        raise HTTPException(status_code=400, detail="Unsupported archive format. ZIP only.")

      result = _scan_archive_bytes(
        contents,
        file.filename or "archive.zip",
        direction,
        file_id
      )
      return {
          "file_id": file_id,
          "original_filename": result["download_name"],
          "file_size": os.path.getsize(result["sanitized_path"]),
          "mime_type": "application/zip",
          "verdict": result["verdict"],
          "risk_level": result["risk_level"],
          "stego_probability": result["stego_probability"],
          "model": "archive_cdr",
          "model_scores": [],
          "aletheia": "SKIPPED_ARCHIVE",
          "archive": {
              "image_count": result["image_count"],
              "suspicious_count": result["suspicious_count"],
              "policy_removed_count": result["policy_removed_count"],
              "policy_findings": result["policy_findings"],
          },
          "sanitized_path": result["sanitized_path"],
      }
    
    try:
        result = _scan_image_bytes(contents, file.filename or "stream", direction, file_id)
        ensemble_result = result.get("ensemble", {})
        return {
            "file_id": file_id,
            "original_filename": file.filename or "stream",
            "file_size": len(contents),
            "mime_type": file.content_type or "application/octet-stream",
            "verdict": result["verdict"],
            "risk_level": result["risk_level"],
            "stego_probability": result["stego_probability"],
            "model": ensemble_result.get("route_model"),
            "model_scores": ensemble_result.get("model_scores", []),
            "aletheia": _aletheia_header_value(result["aletheia"]) if isinstance(result["aletheia"], dict) else result["aletheia"],
            "sanitized_path": result["sanitized_path"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Policy Violation: {str(e)}")
    except Exception as e:
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
    parent_mail_id: int = Form(0),
    attachment_ids: str = Form(""),
    attachment_filenames: str = Form(""),
    attachment_mimetypes: str = Form(""),
    attachment_sizes: str = Form(""),
):
    import json as _json

    now = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()

    parent_mail_id = parent_mail_id or 0

    sender_value = sender.strip()
    recipient_value = recipient.strip()

    saved_attachment_meta = []
    if attachment_ids:
        try:
            ids = _json.loads(attachment_ids)
            filenames = _json.loads(attachment_filenames) if attachment_filenames else []
            mimetypes = _json.loads(attachment_mimetypes) if attachment_mimetypes else []
            sizes = _json.loads(attachment_sizes) if attachment_sizes else []
        except (_json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid attachment metadata")

        if not isinstance(ids, list) or not all(isinstance(values, list) for values in (filenames, mimetypes, sizes)):
            raise HTTPException(status_code=400, detail="Invalid attachment metadata")

        for i, file_id in enumerate(ids):
            if not isinstance(file_id, str) or not file_id.strip():
                raise HTTPException(status_code=400, detail="Invalid attachment file_id")

            original_filename = filenames[i] if i < len(filenames) else "unknown"
            mime_type = mimetypes[i] if i < len(mimetypes) else "application/octet-stream"
            file_size = sizes[i] if i < len(sizes) else 0

            if not isinstance(original_filename, str) or not original_filename.strip():
                raise HTTPException(status_code=400, detail="Invalid attachment filename")
            if not isinstance(mime_type, str) or not mime_type.strip():
                raise HTTPException(status_code=400, detail="Invalid attachment mimetype")
            if not isinstance(file_size, int):
                raise HTTPException(status_code=400, detail="Invalid attachment size")

            saved_attachment_meta.append({
                "file_id": file_id.strip(),
                "original_filename": original_filename,
                "mime_type": mime_type,
                "file_size": file_size,
            })

    conn = sqlite3.connect(MAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 발신자 username 조회
    cursor.execute("""
        SELECT id, email, username
        FROM employee
        WHERE id = ?
          AND b_deleted = 'N'
        LIMIT 1
    """, (sender_value,))
    sender_row = cursor.fetchone()

    if sender_row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="발신자를 찾을 수 없습니다.")

    sender_id = sender_row["id"]
    sender_email = sender_row["email"] or sender_value

    # 수신자 username 조회
    cursor.execute("""
        SELECT id, email, username
        FROM employee
        WHERE id = ?
          AND b_deleted = 'N'
        LIMIT 1
    """, (recipient_value,))
    recipient_row = cursor.fetchone()

    if recipient_row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="수신자를 찾을 수 없습니다.")

    recipient_id = recipient_row["id"]
    recipient_email = recipient_row["email"] or recipient_value

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
    inbox_mail_id = None
    if final_status == "SENT":
        cursor.execute("""
            INSERT INTO mail (sender_id, mailbox_id, parent_mail_id, subject, body, status, sent_at, created_at)
            VALUES (?, ?, ?, ?, ?, 'SENT', ?, ?)
        """, (sender_id, inbox_id, parent_mail_id, subject, body, now, now))
        inbox_mail_id = cursor.lastrowid

    # 스캔 단계에서 저장된 파일을 file_id 기반으로 mail_attachment에 매핑
    saved_attachments = []
    for attachment in saved_attachment_meta:
        file_id = attachment["file_id"]
        original_filename = attachment["original_filename"]
        mime_type = attachment["mime_type"]
        file_size = attachment["file_size"]

        safe_name = _safe_disk_name(original_filename)
        sanitized_path = _find_sanitized_attachment_path(file_id, original_filename)
        stored_path = sanitized_path if sanitized_path else os.path.join(UPLOAD_DIR, f"{file_id}_{safe_name}")

        # 발신자 SENT에 첨부파일 매핑
        cursor.execute("""
            INSERT INTO mail_attachment (mail_id, original_file_name, stored_path, file_size, mime_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (mail_id, original_filename, stored_path, file_size, mime_type, now))

        # 수신자 INBOX에도 동일하게 첨부파일 매핑
        if inbox_mail_id:
            cursor.execute("""
                INSERT INTO mail_attachment (mail_id, original_file_name, stored_path, file_size, mime_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (inbox_mail_id, original_filename, stored_path, file_size, mime_type, now))

        saved_attachments.append({
            "file_id": file_id,
            "original_file_name": original_filename,
            "file_size": file_size,
            "mime_type": mime_type,
        })

        _attach_mail_participants_to_audit(ids, sender_email, recipient_email)

    conn.commit()
    conn.close()

    return {
        "id": mail_id,
        "sender": sender_email,
        "recipient": recipient_email,
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
          e.username AS sender_username,
          e.email
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
                "email": r["email"] or "",
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
# 메일 삭제
# DELETE /mails/{id}
# ─────────────────────────────────────────────────
@app.delete("/mails/{mail_id}")
async def delete_mail(mail_id: int):
    conn = sqlite3.connect(MAIL_DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE mail
        SET b_deleted = 'Y'
        WHERE id = ?
        """,
        (mail_id,),
    )

    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="처리할 메일을 찾을 수 없습니다.")

    conn.commit()
    conn.close()
    return {"id": mail_id, "status": "DELETE"}

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

    # S3 버킷이 설정된 경우 presigned URL 발급
    if S3_BUCKET:
        filename = os.path.basename(stored_path)
        if SANITIZED_DIR in stored_path:
            s3_key = f"sanitized/{filename}"
        elif QUARANTINE_DIR in stored_path:
            raise HTTPException(status_code=403, detail="차단된 파일은 다운로드할 수 없습니다.")
        else:
            s3_key = f"uploads/{filename}"

        try:
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": S3_BUCKET,
                    "Key": s3_key,
                    "ResponseContentDisposition": f"attachment; filename*=UTF-8''{quote(attachment['original_file_name'])}",
                    "ResponseContentType": attachment["mime_type"] or "application/octet-stream",
                },
                ExpiresIn=300,  # 5분
            )
            return {"download_url": presigned_url, "expires_in": 300}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"다운로드 URL 생성 실패: {str(e)}")

    # S3 미설정 시 로컬 파일 반환 (개발 환경 fallback)
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
        SELECT
            file_id,
            file_name,
            stego_probability,
            decoded_message,
            processed_at,
            risk_level,
            action,
            original_kb,
            sanitized_kb,
            avg_pixel_diff
        FROM cdr_logs
        ORDER BY processed_at DESC
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        "total_count": len(rows),
        "logs": rows
    }

# ─────────────────────────────────────────────────
# file_id 기반 저장 파일 탐색
# 원본 업로드, 격리, 무해화 디렉토리에서 순차 검색
# ─────────────────────────────────────────────────
def _find_file_by_id(file_id: str, target: str = "original"):
    search_dirs = []

    if target == "sanitized":
        search_dirs = [SANITIZED_DIR]
    else:
        search_dirs = [UPLOAD_DIR, QUARANTINE_DIR]

    for directory in search_dirs:
        for filename in os.listdir(directory):
            if filename.startswith(file_id):
                return os.path.join(directory, filename), filename

    return None, None


# ─────────────────────────────────────────────────
# 스테가노그래피 디코딩 API
# POST /decode
# file_id 기반 원본 이미지에서 은닉 메시지 추출
# 파일명에 따라 LSB / DCT / DWT 디코더 자동 선택
# ─────────────────────────────────────────────────
@app.post("/decode")
async def decode_stego_message(payload: dict):
    file_id = payload.get("file_id")
    target = payload.get("target", "original")
    decoder_type = payload.get("decoder_type")

    if not file_id:
        raise HTTPException(status_code=400, detail="file_id is required")

    matched_path, matched_name = _find_file_by_id(file_id, target)

    if matched_path is None:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    name_lower = matched_name.lower()

    # decoder_type을 프론트에서 안 보내면 파일명으로 자동 판단
    if decoder_type is None:
        if "dct" in name_lower:
            decoder_type = "DCT"
        elif "dwt" in name_lower:
            decoder_type = "DWT"
        else:
            decoder_type = "LSB"

    decoder_type = decoder_type.upper()

    # 디코더 선택
    if decoder_type == "DCT":
        decoded_message = _decode_dct_message(matched_path)
    elif decoder_type == "DWT":
        decoded_message = _decode_dwt_message(matched_path)
    else:
        decoded_message = _decode_lsb_message(matched_path)
        decoder_type = "LSB"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 디코딩 결과를 CDR 검증 로그에 저장
    cursor.execute("""
        UPDATE cdr_logs
        SET decoded_message = ?
        WHERE file_id = ?
    """, (decoded_message, file_id))

    cursor.execute("""
        SELECT file_name
        FROM cdr_logs
        WHERE file_id = ?
        LIMIT 1
    """, (file_id,))

    row = cursor.fetchone()

    conn.commit()
    conn.close()

    return {
        "file_id": file_id,
        "file_name": row[0] if row else matched_name,
        "decoded_message": decoded_message,
        "message_length": len(decoded_message) if decoded_message else 0,
        "decoder_type": decoder_type
    }


# ─────────────────────────────────────────────────
# LSB 테스트 이미지 생성
# POST /debug/make-lsb
# HELLO CDR 메시지를 숨긴 PNG 생성
# ─────────────────────────────────────────────────
@app.post("/debug/make-lsb")
async def make_lsb_test_image():
    from PIL import Image

    file_id = str(uuid.uuid4())[:8]
    file_name = "lsb_test.png"
    input_filename = f"{file_id}_{file_name}"
    input_path = os.path.join(UPLOAD_DIR, input_filename)

    img = Image.new("RGB", (200, 200), color=(120, 180, 220))
    pixels = list(img.getdata())

    message = "HELLO CDR" + "\x00"
    bits = "".join(f"{ord(c):08b}" for c in message)

    new_pixels = []
    bit_idx = 0

    for r, g, b in pixels:
        channels = [r, g, b]

        for i in range(3):
            if bit_idx < len(bits):
                channels[i] = (channels[i] & ~1) | int(bits[bit_idx])
                bit_idx += 1

        new_pixels.append(tuple(channels))

    img.putdata(new_pixels)
    img.save(input_path, "PNG")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cdr_logs
        (file_id, file_name, stego_probability, decoded_message, processed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        file_id,
        file_name,
        99.9,
        None,
        datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
    ))
    conn.commit()
    conn.close()

    return {
        "file_id": file_id,
        "file_name": file_name,
        "message": "HELLO CDR"
    }

@app.get("/cdr/original/{file_id}")
def get_original_image(file_id: str):
    matched_path, matched_name = _find_file_by_id(file_id, "original")

    if matched_path is None:
        raise HTTPException(status_code=404, detail="원본 파일을 찾을 수 없습니다.")

    name_lower = matched_name.lower()

    if name_lower.endswith(".png"):
        media_type = "image/png"
    elif name_lower.endswith(".jpg") or name_lower.endswith(".jpeg"):
        media_type = "image/jpeg"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=matched_path,
        media_type=media_type,
        filename=matched_name,
    )


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
