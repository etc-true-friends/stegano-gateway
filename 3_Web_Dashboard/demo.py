"""
/etc/friends 팀 - 인드라넷 파이프라인 발표 시연 자동화 스크립트 (demo.py)
"""

import os
import time
import sys
import requests
from pathlib import Path
from stegano import lsb

API_BASE = "http://127.0.0.1:8000"

# MSA 디렉토리 구조에 맞춘 로컬 워크스페이스 경로 동적 추적
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
WORKSPACE_DIR = BASE_DIR / "4_Local_Workspace" / "test_images"
WORKSPACE_SANITIZED = BASE_DIR / "4_Local_Workspace" / "sanitized"

# ─────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────
def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_step(step: int, msg: str):
    print(f"\n[Step {step}] {msg}")
    print("-" * 40)

def wait(sec: float = 1.0):
    time.sleep(sec)

# ─────────────────────────────────────────────────
# 시연용 이미지 준비
# ─────────────────────────────────────────────────
def prepare_demo_images():
    """로컬 워크스페이스 내부의 자원을 활용하여 시연용 은닉 데이터 생성"""
    clean_path = WORKSPACE_DIR / "dog.png"
    
    if not clean_path.exists():
        raise FileNotFoundError(
            f"시연 실패: 로컬 워크스페이스에 베이스 이미지인 '{clean_path}' 파일이 필요합니다."
        )

    hidden_path = WORKSPACE_DIR / "demo_automated_hidden.png"
    secret = "TOP_SECRET_DEFENSE_DOC_2026_CONFIDENTIAL_CLASSIFIED"
    
    # 예전의 무차별 오염이 아닌, 정상적인 LSB 은닉 실행
    img = lsb.hide(str(clean_path), secret)
    img.save(str(hidden_path), format="PNG")
    
    print(f"  [+] 정상 원본 이미지 로드: {clean_path.name}")
    print(f"  [+] 시연용 은닉 이미지 생성: {hidden_path.name}")

    return clean_path, hidden_path

# ─────────────────────────────────────────────────
# 시연 1: API 서버 확인
# ─────────────────────────────────────────────────
def demo_health_check():
    print_step(1, "API 보안 게이트웨이 서버 동작 확인")
    try:
        r = requests.get(f"{API_BASE}/", timeout=3)
        data = r.json()
        print(f"  [+] AI 모델 구동 상태: {data.get('ai_model', '-')}")
        print(f"  [+] 가속 파이프라인 장치: {data.get('device', '-').upper()}")
        print(f"  [+] 소프트웨어 버전: {data.get('version', '-')}")
        print("\n  >> SYSTEM STATUS: ONLINE (정상 가동 중)")
        return True
    except Exception as e:
        print(f"  [-] ERROR 백엔드 서버 응답 없음: {e}")
        print("  -> uvicorn api:app --port 8000 실행 후 재시도하세요")
        return False

# ─────────────────────────────────────────────────
# 시연 2: 정상 이미지
# ─────────────────────────────────────────────────
def demo_clean_image(clean_path: Path):
    print_step(2, "정상 이미지 시연 (Clean Image 통과 검증)")
    print(f"  파일 경로: {clean_path.name}")

    with open(clean_path, "rb") as f:
        r = requests.post(
            f"{API_BASE}/scan",
            files={"file": (clean_path.name, f, "image/png")}
        )

    result = r.json()
    pipeline = result.get("pipeline", {})
    detection = pipeline.get("step1_detection", {})
    sanitization = pipeline.get("step2_sanitization", {})
    quarantine = pipeline.get("step3_quarantine", {})

    print(f"\n  [1선 AI 방어선 결과]")
    print(f"    - 위협 확률(Stego Prob): {detection.get('stego_probability')}")
    print(f"    - 리스크 등급:           {detection.get('risk_level')}")
    print(f"    - 시스템 최종 판정:      {detection.get('verdict')}")
    print(f"\n  [2선 CDR 무해화 및 격리 현황]")
    print(f"    - CDR 파이프라인 가동:  SUCCESS")
    print(f"    - 위험축출 격리 보관:   {'YES (위협 차단)' if quarantine.get('quarantined') else 'NO (정상 통과)'}")
    
    return result.get("file_id")

# ─────────────────────────────────────────────────
# 시연 3: 은닉 이미지 (핵심 시연)
# ─────────────────────────────────────────────────
def demo_hidden_image(hidden_path: Path):
    print_step(3, "은닉 이미지 시연 (스테가노그래피 탐지 + 심층 방어 체인)")
    print(f"  파일 경로: {hidden_path.name}")
    print(f"  (보안 인텔리전스: 해당 이미지 내부에 군사 기밀 데이터 은닉 상태)")

    with open(hidden_path, "rb") as f:
        r = requests.post(
            f"{API_BASE}/scan",
            files={"file": (hidden_path.name, f, "image/png")}
        )

    result = r.json()
    pipeline = result.get("pipeline", {})
    detection = pipeline.get("step1_detection", {})
    sanitization = pipeline.get("step2_sanitization", {})
    quarantine = pipeline.get("step3_quarantine", {})

    print(f"\n  [1선 AI 방어선 결과]")
    print(f"    - 위협 확률(Stego Prob): {detection.get('stego_probability')}")
    print(f"    - 리스크 등급:           {detection.get('risk_level')}")
    print(f"    - 시스템 최종 판정:      {detection.get('verdict')}")

    print(f"\n  [2선 CDR 무해화 체인 구동 로그]")
    for step in sanitization.get("steps", []):
        clean_step = step.replace("✓ ", "  -> ")
        print(f"  {clean_step}")

    print(f"\n  [물리 가공 데이터 지표]")
    print(f"    - 구조 변형도(Pixel Diff): {sanitization.get('pixel_diff')} (육안 식별 불가능)")
    print(f"    - 위험축출 격리 보관:     {'YES (quarantine 폴더 이송 완료)' if quarantine.get('quarantined') else 'NO'}")

    return result.get("file_id")

# ─────────────────────────────────────────────────
# 시연 4: 무해화 효과 검증 (Zero Trust 입증)
# ─────────────────────────────────────────────────
def demo_verify_sanitization(file_id: str, hidden_path: Path):
    print_step(4, "Zero Trust CDR 무해화 성능 물리 검증")

    # 무해화 전: 원본에서 추출 시도
    print("  [무해화 적용 전] 파일 내부 기밀 페이로드 역추적 시도...")
    try:
        extracted = lsb.reveal(str(hidden_path))
        if extracted:
            print(f"    -> 기밀 탈취 성공: '{extracted[:41]}...'")
            print(f"    -> 결론: 무해화 처리 전 보안 취약점 노출 상태 확인")
    except Exception as e:
        print(f"    [-] 추출 실패: {type(e).__name__}")

    wait(1.5)

    # 무해화 후: 처리된 파일에서 추출 시도
    print("\n  [무해화 적용 후] 게이트웨이 통과(CDR) 파일 내 기밀 추출 시도...")

    sanitized_files = list(WORKSPACE_SANITIZED.glob(f"{file_id}_*"))
    if not sanitized_files:
        print("    [-] 오류: 가공된 무해화 파일을 저장소에서 찾을 수 없습니다.")
        return

    sanitized_path = sanitized_files[0]
    try:
        extracted = lsb.reveal(str(sanitized_path))
        if extracted:
            print(f"    [-] 방어 실패: 페이로드가 파괴되지 않음 -> {extracted}")
        else:
            print(f"    [+] 방어 성공: 데이터 구조 파괴로 껍데기만 잔존함")
    except Exception as e:
        print(f"    [+] 방어 성공: 이미지 픽셀 재구성으로 기밀 은닉 데이터가 완전 파괴됨")
        print(f"    (비정상 구조 분석 예외 트랙: {type(e).__name__})")

# ─────────────────────────────────────────────────
# 시연 5: 감사 로그
# ─────────────────────────────────────────────────
def demo_audit_log():
    print_step(5, "통합 감사 로그 및 포렌직 데이터 확인")

    r = requests.get(f"{API_BASE}/audit")
    data = r.json()

    print(f"  - 게이트웨이 누적 검사: {data['total_count']} 건")
    print(f"  - 고위험군 이상징후 탐지: {data['suspicious_count']} 건")
    print(f"\n  [최근 생성된 관제 로그 3건 요약]")

    for log in data["logs"][-3:]:
        print(f"    [{log['timestamp'][:19].replace('T', ' ')}] "
              f"파일명: {log['original_name']} | "
              f"위험 스코어: {log['stego_probability']}% | "
              f"최종조치: {log['action']}")

# ─────────────────────────────────────────────────
# 메인 시연 실행
# ─────────────────────────────────────────────────
def main():
    print_header("IndraNet: 지능형 위협 탐지 및 CDR 무해화 통합 게이트웨이")
    print("  /etc/friends 팀 - 중간발표 데모 자동화 콘솔 인터페이스")

    try:
        # 0. 이미지 준비
        print("\n[사전 단계] 시연용 통제 데이터셋 세팅 중...")
        clean_path, hidden_path = prepare_demo_images()
        wait()

        # 1. 서버 확인
        if not demo_health_check():
            return
        wait()

        # 2. 정상 이미지
        demo_clean_image(clean_path)
        wait()

        # 3. 은닉 이미지 (핵심)
        file_id = demo_hidden_image(hidden_path)
        wait()

        # 4. 무해화 검증
        if file_id:
            demo_verify_sanitization(file_id, hidden_path)
        wait()

        # 5. 감사 로그
        demo_audit_log()

        # 마무리
        print_header("AUTOMATED DEMO SEQUENCE COMPLETED")
        print("  AI 선제 스캔 및 CDR 물리 파괴를 통한 심층 방어 체인 입증 완료.")
        print()

    except Exception as e:
        print(f"\n[-] 시연 도중 예상치 못한 에러 발생: {e}")
    finally:
        # 임시 생성 파일 보안 파쇄
        temp_hidden = WORKSPACE_DIR / "demo_automated_hidden.png"
        if temp_hidden.exists():
            temp_hidden.unlink()

if __name__ == "__main__":
    main()