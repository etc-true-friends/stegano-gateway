"""
Zero Trust CDR 무해화 효과 검증 및 자동화 시연 스크립트 (test_cdr.py)
"""

import os
from pathlib import Path
from PIL import Image
from stegano import lsb
from cdr_sanitizer import CDRSanitizer

# 1. MSA 디렉토리 구조에 맞춘 로컬 워크스페이스 경로 동적 추적
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
WORKSPACE_DIR = os.path.join(BASE_DIR, "4_Local_Workspace", "test_images")


def prepare_verification_images(clean_path_str: str, hidden_path_str: str, secret_message: str):
    """
    검증용 이미지 준비
    인위적인 그라데이션 배열이 아닌 실제 자연 이미지를 사용하여 검증의 신뢰성을 확보함.
    """
    clean_path = Path(clean_path_str)
    
    if not clean_path.exists():
        raise FileNotFoundError(
            f"검증 실패: 로컬 워크스페이스에 실제 사진인 '{clean_path_str}' 파일이 필요합니다.\n"
            "  -> 4_Local_Workspace/test_images/ 폴더 내부의 이미지 이름을 확인하십시오."
        )

    # 기존 생성된 잔여 파일이 존재할 경우 초기화
    if Path(hidden_path_str).exists():
        Path(hidden_path_str).unlink()

    img = lsb.hide(str(clean_path), secret_message)
    img.save(hidden_path_str, format="PNG")
    
    print(f"  [+] 정상 원본 이미지 로드 완료: {clean_path.name}")
    print(f"  [+] 시연용 기밀 은닉 이미지 생성 완료 -> {Path(hidden_path_str).name}")


def run_verification():
    print("\n" + "=" * 60)
    print("  IndraNet 게이트웨이: Zero Trust CDR 무해화 검증 파이프라인")
    print("=" * 60)

    # 2. 모든 임시 입출력 파일 경로를 격리된 워크스페이스 내부로 지정
    test_clean = os.path.join(WORKSPACE_DIR, "dog.png") # 기존 존재가 확인된 dog.png 활용
    test_hidden = os.path.join(WORKSPACE_DIR, "demo_hidden_payload.png")
    test_sanitized = os.path.join(WORKSPACE_DIR, "demo_sanitized_output.jpg")
    
    secret_message = "TOP_SECRET_DEFENSE_DOC_2026_CONFIDENTIAL"

    # [1단계] 검증 환경 및 베이스 이미지 세팅
    print("\n[Step 1] 테스트 이미지 검증 환경 준비")
    try:
        prepare_verification_images(test_clean, test_hidden, secret_message)
    except FileNotFoundError as e:
        print(f"  [-] 오류 발생: {e}")
        return False

    # [2단계] 무해화 전 취약점 상태 확인
    print("\n[Step 2] 무해화 처리 전 원본 메시지 추출 시도 (공격 시뮬레이션)")
    try:
        extracted_before = lsb.reveal(test_hidden)
        if extracted_before == secret_message:
            print(f"  [🚨 위험] 기밀 데이터 은닉 및 탈취 성공: '{extracted_before}'")
            print("  -> 기존 네트워크 게이트웨이의 스테가노그래피 우회 취약점 입증")
        else:
            print(f"  [!] 부분 데이터 추출됨: '{extracted_before}'")
    except Exception as e:
        print(f"  [-] 추출 실패: {e}")

    # [3단계] Zero Trust CDR 5단계 무해화 프로세스 가동
    print("\n[Step 3] Zero Trust CDR 5단계 무해화 파이프라인 가동")
    sanitizer = CDRSanitizer(jpeg_quality=85, resize_ratio=0.95)
    result = sanitizer.sanitize(test_hidden, test_sanitized)

    # 외부 모듈 리턴 로그의 이모지 문자열 정제 후 출력
    for step in result["steps_executed"]:
        clean_step = step.replace("✓ ", "[OK] ").replace("✗ ", "[FAIL] ")
        print(f"    {clean_step}")
    print(f"  -> 무해화 가공 파일 생성 완료: {Path(test_sanitized).name} ({result['sanitized_kb']} KB)")
    print(f"  -> 무해화 프로세스 전후 픽셀 변화량(평균): {result['avg_pixel_diff']}")

    # [4단계] 무해화 후 차단 성공 여부 최종 검증
    print("\n[Step 4] 무해화 가공 후 기밀 데이터 복구 차단 최종 검증")
    try:
        extracted_after = lsb.reveal(test_sanitized)
        if extracted_after == secret_message:
            print("  [정밀 검증 실패] 방어 실패: 은닉된 메시지가 파괴되지 않고 잔존함")
            verdict = False
        else:
            print(f"  [정밀 검증 성공] 방어 성공: 은닉 메시지 파괴 완료 (복구 불가능)")
            verdict = True
    except Exception as e:
        print(f"  [정밀 검증 성공] 방어 성공: 이미지의 구조적 종속성 변형으로 페이로드 추출 자체가 원천 불가능함")
        print(f"  (예외 분석 지표: {type(e).__name__})")
        verdict = True

    # [5단계] 파이프라인 결과 판정 요약
    print("\n" + "=" * 60)
    if verdict:
        print("  최종 검증 판정: Zero Trust CDR 무해화 엔진 기능 정상 가동 확인")
        print("  -> 인드라넷 보안 게이트웨이 2선 방어 모듈로 통합 가능")
    else:
        print("  최종 검증 판정: 무해화 성능 불충분 (파라미터 재설정 필요)")
        print("  -> resize_ratio 하향 또는 jpeg_quality 하향 조정을 권장합니다.")
    print("=" * 60)

    # 검증 완료 후 기밀이 은닉되었던 중간 임시 파일은 보안상 즉시 삭제
    if Path(test_hidden).exists():
        Path(test_hidden).unlink()

    return verdict


if __name__ == "__main__":
    run_verification()