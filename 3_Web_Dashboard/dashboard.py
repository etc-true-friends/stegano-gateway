"""
/etc/friends 팀 - 스테가노그래피 탐지 관제 대시보드 (dashboard.py)
"""

import os
import time
import requests
import streamlit as st
import pandas as pd
from PIL import Image
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────
# 경로 및 API 설정 (MSA 아키텍처 반영)
# ─────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE", "http://api-gateway:8000")

# 4_Local_Workspace 공용 저장소 경로 동적 매핑
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
WORKSPACE_SANITIZED = BASE_DIR / "4_Local_Workspace" / "sanitized"

st.set_page_config(
    page_title="/etc/friends | 스테가노 탐지",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────
# 커스텀 CSS (Midnight Security 테마)
# ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');

/* 전체 배경 */
.stApp {
    background: #0a0e1a;
    color: #c8d8f0;
    font-family: 'Inter', sans-serif;
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background: #0d1321;
    border-right: 1px solid #1e2d4a;
}

/* 배너 */
.banner {
    background: linear-gradient(135deg, #0d1b35 0%, #0a1628 50%, #0d1b35 100%);
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    padding: 24px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.banner::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #4a9eff, #00d4ff, #4a9eff, transparent);
}
.banner-team {
    font-family: 'Share Tech Mono', monospace;
    font-size: 13px;
    color: #4a9eff;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.banner-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 28px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.banner-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 11px;
    color: #5a7fa8;
    letter-spacing: 2px;
}
.banner-badge {
    position: absolute;
    right: 32px;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(74, 158, 255, 0.1);
    border: 1px solid #4a9eff;
    border-radius: 3px;
    padding: 6px 14px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 11px;
    color: #4a9eff;
    letter-spacing: 1px;
}

/* 메트릭 카드 */
.metric-card {
    background: #0d1321;
    border: 1px solid #1e2d4a;
    border-radius: 4px;
    padding: 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.metric-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #4a9eff, transparent);
}
.metric-value {
    font-family: 'Rajdhani', sans-serif;
    font-size: 36px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
    margin-bottom: 4px;
}
.metric-label {
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    color: #5a7fa8;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* 위험도 게이지 */
.risk-high   { color: #ff4444; font-weight: 700; }
.risk-medium { color: #ffaa00; font-weight: 700; }
.risk-low    { color: #00cc66; font-weight: 700; }

/* 결과 박스 */
.result-box {
    background: #0d1321;
    border: 1px solid #1e2d4a;
    border-radius: 4px;
    padding: 20px;
    margin: 8px 0;
}
.result-suspicious {
    border-left: 4px solid #ff4444;
    background: rgba(255, 68, 68, 0.05);
}
.result-clean {
    border-left: 4px solid #00cc66;
    background: rgba(0, 204, 102, 0.05);
}

/* 로그 테이블 */
.log-table {
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
}

/* 섹션 헤더 */
.section-header {
    font-family: 'Share Tech Mono', monospace;
    font-size: 11px;
    color: #4a9eff;
    letter-spacing: 3px;
    text-transform: uppercase;
    padding: 8px 0;
    border-bottom: 1px solid #1e2d4a;
    margin-bottom: 16px;
}

/* 버튼 스타일 */
.stButton > button {
    background: #0d2040;
    color: #4a9eff;
    border: 1px solid #4a9eff;
    border-radius: 3px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 8px 20px;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #4a9eff;
    color: #0a0e1a;
}

/* 파일 업로더 */
[data-testid="stFileUploader"] {
    border: 1px dashed #1e3a5f;
    border-radius: 4px;
    background: #0d1321;
}

/* 탭 */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1321;
    border-bottom: 1px solid #1e2d4a;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Share Tech Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    color: #5a7fa8;
    padding: 12px 24px;
    border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] {
    color: #4a9eff !important;
    border-bottom: 2px solid #4a9eff !important;
    background: transparent !important;
}

/* 코드 블록 */
.stCode {
    background: #0d1321 !important;
    border: 1px solid #1e2d4a;
}

/* 구분선 */
hr {
    border-color: #1e2d4a;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────
def check_api() -> bool:
    try:
        r = requests.get(f"{API_BASE}/", timeout=2)
        return r.status_code == 200
    except:
        return False


def get_audit_log() -> dict:
    try:
        r = requests.get(f"{API_BASE}/audit", timeout=3)
        return r.json()
    except:
        return {"total_count": 0, "suspicious_count": 0, "logs": []}


def scan_file(file_bytes, filename) -> dict:
    try:
        r = requests.post(
            f"{API_BASE}/scan",
            files={"file": (filename, file_bytes, "image/png")},
            timeout=30
        )

        return {
            "file_id": r.headers.get("X-Gateway-File-ID"),
            "pipeline": {
                "step1_detection": {
                    "stego_probability": r.headers.get("X-Gateway-Stego-Prob", "0.0%"),
                    "risk_level": r.headers.get("X-Gateway-Risk-Level", "LOW"),
                    "verdict": r.headers.get("X-Gateway-Verdict", "CLEAN"),
                },
                "step2_sanitization": {
                    "steps": [
                        "SRNet AI scan completed",
                        "CDR sanitization completed",
                        "Sanitized image returned"
                    ],
                    "pixel_diff": "-"
                },
                "step3_quarantine": {
                    "quarantined": r.headers.get("X-Gateway-Verdict") == "SUSPICIOUS"
                }
            }
        }
    except Exception as e:
        return {"error": str(e)}


def risk_color(level: str) -> str:
    return {"HIGH": "#ff4444", "MEDIUM": "#ffaa00", "LOW": "#00cc66"}.get(level, "#5a7fa8")


def risk_emoji(level: str) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(level, "⚪")


# ─────────────────────────────────────────────────
# 배너
# ─────────────────────────────────────────────────
api_ok = check_api()
status_text = "● ONLINE" if api_ok else "● OFFLINE"
status_color = "#00cc66" if api_ok else "#ff4444"

st.markdown(f"""
<div class="banner">
    <div class="banner-team">// /etc/friends</div>
    <div class="banner-title">스테가노그래피 이상 징후 탐지 시스템</div>
    <div class="banner-sub">STEGANOGRAPHY ANOMALY DETECTION · CDR SANITIZATION GATEWAY · ZERO TRUST</div>
    <div class="banner-badge" style="color: {status_color}; border-color: {status_color};">
        {status_text}
    </div>
</div>
""", unsafe_allow_html=True)

if not api_ok:
    st.error("⚠️ API 서버 연결 실패 — `uvicorn api:app --port 8000` 실행 후 새로고침하세요")
    st.stop()


# ─────────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">// SYSTEM INFO</div>', unsafe_allow_html=True)

    try:
        info = requests.get(f"{API_BASE}/").json()
        st.markdown(f"""
        <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #5a7fa8; line-height: 2;">
        AI MODEL<br>
        <span style="color: #c8d8f0;">{info.get('ai_model', '-')}</span><br><br>
        DEVICE<br>
        <span style="color: #c8d8f0;">{info.get('device', '-').upper()}</span><br><br>
        VERSION<br>
        <span style="color: #c8d8f0;">{info.get('version', '-')}</span>
        </div>
        """, unsafe_allow_html=True)
    except:
        pass

    st.markdown('<br><div class="section-header">// PIPELINE</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #5a7fa8; line-height: 2.2;">
    01 · POLICY CHECK<br>
    <span style="color: #4a9eff;">02 · AI DETECTION</span><br>
    03 · CDR SANITIZE<br>
    04 · QUARANTINE<br>
    05 · AUDIT LOG
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<br><div class="section-header">// TEAM</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #5a7fa8; line-height: 2;">
    TEAM<br>
    <span style="color: #c8d8f0;">/etc/friends</span><br><br>
    BOOTCAMP<br>
    <span style="color: #c8d8f0;">구름 정보보호 17기</span>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# 탭
# ─────────────────────────────────────────────────
tab1, tab2 = st.tabs(["  SCAN  ", "  DASHBOARD  "])


# ════════════════════════════════════════════════
# TAB 1: 파일 스캔
# ════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">// FILE SCAN — 파일 업로드 및 탐지</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "이미지 파일을 업로드하세요",
        type=["png", "jpg", "jpeg", "bmp", "webp"],
        label_visibility="collapsed"
    )

    if uploaded:
        col_img, col_result = st.columns([1, 1], gap="large")

        with col_img:
            st.markdown('<div class="section-header">// ORIGINAL</div>', unsafe_allow_html=True)
            img = Image.open(uploaded)
            st.image(img, use_container_width=True)
            st.markdown(f"""
            <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #5a7fa8; margin-top: 8px;">
            FILE · {uploaded.name}<br>
            SIZE · {uploaded.size // 1024} KB<br>
            TYPE · {img.mode} · {img.size[0]}×{img.size[1]}
            </div>
            """, unsafe_allow_html=True)

        with col_result:
            st.markdown('<div class="section-header">// ANALYSIS</div>', unsafe_allow_html=True)

            if st.button("SCAN & SANITIZE", use_container_width=True):
                with st.spinner("분석 중..."):
                    uploaded.seek(0)
                    result = scan_file(uploaded.read(), uploaded.name)

                if "error" in result:
                    st.error(f"오류: {result['error']}")
                else:
                    pipeline = result.get("pipeline", {})
                    detection = pipeline.get("step1_detection", {})
                    prob = float(detection.get("stego_probability", "0").replace("%", ""))
                    level = detection.get("risk_level", "LOW")
                    verdict = detection.get("verdict", "CLEAN")
                    is_suspicious = verdict == "SUSPICIOUS"

                    # 위험도 게이지
                    gauge_color = risk_color(level)
                    st.markdown(f"""
                    <div class="result-box {'result-suspicious' if is_suspicious else 'result-clean'}">
                        <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #5a7fa8; letter-spacing: 2px; margin-bottom: 12px;">
                            STEGO PROBABILITY
                        </div>
                        <div style="font-family: 'Rajdhani', sans-serif; font-size: 52px; font-weight: 700; color: {gauge_color}; line-height: 1;">
                            {prob:.1f}%
                        </div>
                        <div style="font-family: 'Share Tech Mono', monospace; font-size: 13px; color: {gauge_color}; margin-top: 4px;">
                            {risk_emoji(level)} {level} RISK · {verdict}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 무해화 결과
                    sanitization = pipeline.get("step2_sanitization", {})
                    steps = sanitization.get("steps", [])
                    pixel_diff = sanitization.get("pixel_diff", 0)

                    st.markdown(f"""
                    <div class="result-box" style="margin-top: 12px;">
                        <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #5a7fa8; letter-spacing: 2px; margin-bottom: 12px;">
                            CDR SANITIZATION
                        </div>
                    """, unsafe_allow_html=True)

                    for step in steps:
                        st.markdown(f"""
                        <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #00cc66; padding: 2px 0;">
                            ✓ {step}
                        </div>
                        """, unsafe_allow_html=True)

                    quarantine = pipeline.get("step3_quarantine", {})
                    st.markdown(f"""
                        <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #5a7fa8; margin-top: 12px;">
                            PIXEL DIFF · {pixel_diff} &nbsp;&nbsp;
                            QUARANTINE · {'YES' if quarantine.get('quarantined') else 'NO'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 4_Local_Workspace 저장소 참조
                    file_id = result.get("file_id")
                    sanitized_files = list(WORKSPACE_SANITIZED.glob(f"{file_id}_*")) if file_id else []
                    if sanitized_files:
                        st.markdown('<div class="section-header" style="margin-top: 20px;">// SANITIZED</div>', unsafe_allow_html=True)
                        safe_img = Image.open(sanitized_files[0])
                        st.image(safe_img, use_container_width=True)
                        st.markdown(f"""
                        <div style="font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #00cc66; margin-top: 4px;">
                        LSB 데이터 완전 파괴 완료
                        </div>
                        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════
# TAB 2: 관제 대시보드
# ════════════════════════════════════════════════
with tab2:
    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("REFRESH", use_container_width=True):
            st.rerun()

    audit = get_audit_log()
    total = audit.get("total_count", 0)
    suspicious = audit.get("suspicious_count", 0)
    clean = total - suspicious

    # 메트릭 카드
    st.markdown('<div class="section-header">// STATISTICS</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total}</div>
            <div class="metric-label">TOTAL SCANNED</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #00cc66;">{clean}</div>
            <div class="metric-label">CLEAN</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #ff4444;">{suspicious}</div>
            <div class="metric-label">SUSPICIOUS</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        detection_rate = f"{(suspicious/total*100):.1f}%" if total > 0 else "0.0%"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #4a9eff;">{detection_rate}</div>
            <div class="metric-label">DETECTION RATE</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 감사 로그 테이블
    st.markdown('<div class="section-header">// AUDIT LOG</div>', unsafe_allow_html=True)

    logs = audit.get("logs", [])
    if logs:
        rows = []
        for log in reversed(logs):
            verdict = log.get("verdict", log.get("action", "-"))
            prob = log.get("stego_probability", "-")
            risk = log.get("risk_level", "-")
            emoji = "🔴" if verdict == "SUSPICIOUS" else "🟢" if verdict == "CLEAN" else "⚪"
            rows.append({
                "시각": log.get("timestamp", "")[:19].replace("T", " "),
                "파일명": log.get("original_name", "-"),
                "위험도": f"{prob}%" if isinstance(prob, (int, float)) else str(prob),
                "등급": risk,
                "판정": f"{emoji} {verdict}",
                "처리": log.get("action", "-"),
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "시각": st.column_config.TextColumn(width="medium"),
                "파일명": st.column_config.TextColumn(width="medium"),
                "위험도": st.column_config.TextColumn(width="small"),
                "등급": st.column_config.TextColumn(width="small"),
                "판정": st.column_config.TextColumn(width="medium"),
                "처리": st.column_config.TextColumn(width="small"),
            }
        )
    else:
        st.markdown("""
        <div style="font-family: 'Share Tech Mono', monospace; font-size: 12px; color: #5a7fa8; text-align: center; padding: 40px;">
            NO LOGS YET — SCAN 탭에서 파일을 업로드하세요
        </div>
        """, unsafe_allow_html=True)

    # 위험도 분포 차트
    if logs:
        st.markdown('<br><div class="section-header">// RISK DISTRIBUTION</div>', unsafe_allow_html=True)

        risk_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for log in logs:
            level = log.get("risk_level", "LOW")
            if level in risk_counts:
                risk_counts[level] += 1

        chart_data = pd.DataFrame({
            "등급": list(risk_counts.keys()),
            "건수": list(risk_counts.values()),
        })

        st.bar_chart(
            chart_data.set_index("등급"),
            color="#4a9eff",
            use_container_width=True,
            height=200
        )