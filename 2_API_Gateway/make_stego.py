"""
탐지 모델 검증용 데이터셋 생성 스크립트 (해상도 표준화 로직 적용)
"""
import os
from PIL import Image
from stegano import lsb

def generate_controlled_dataset(raw_image_path: str, cover_output: str, stego_output: str):
    if not os.path.exists(raw_image_path):
        raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {raw_image_path}")

    # 1. 고해상도 원본 이미지를 로드 후 모델 규격(256x256)으로 강제 리사이즈
    img = Image.open(raw_image_path).convert("RGB")
    img = img.resize((256, 256), Image.LANCZOS)
    
    # 2. 인코딩 풋프린트 동기화 (PNG 변환)
    img.save(cover_output, format="PNG")
    print(f"Cover 통제 데이터 생성 완료 (256x256): {cover_output}")

    # 3. 현실적인 페이로드 삽입
    secret_message = "DETECTION_TEST_DATA_2026_SECURITY_LOG_ANALYSIS_" * 10
    
    # 256x256으로 축소된 Cover 이미지를 베이스로 데이터를 은닉
    stego_img = lsb.hide(cover_output, secret_message)
    stego_img.save(stego_output, format="PNG")
    print(f"Stego 통제 데이터 생성 완료 (256x256): {stego_output}")

if __name__ == "__main__":
    # [수정됨] 4_Local_Workspace 내부의 test_images 경로로 업데이트
    WORKSPACE_DIR = "../4_Local_Workspace/test_images"
    
    raw_path = os.path.join(WORKSPACE_DIR, "marek-piwnicki-Q8VPBnw_5PA-unsplash.jpg")
    cover_path = os.path.join(WORKSPACE_DIR, "cover_natural_test.png")
    stego_path = os.path.join(WORKSPACE_DIR, "stego_natural_test.png")
    
    print("규격화된 환경의 테스트 데이터 생성을 시작합니다...")
    generate_controlled_dataset(raw_path, cover_path, stego_path)
    print("작업 완료. 해당 데이터를 통해 API 모델 탐지 테스트를 진행하십시오.")