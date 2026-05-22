"""
CDR (Content Disarm & Reconstruction) 5단계 무해화 파이프라인
==============================================================
스테가노그래피로 은닉된 LSB 데이터를 물리적으로 파괴하는
다단계 이미지 재가공 엔진.

작성: 쿼카님 파이널 프로젝트 (방산 망연계 게이트웨이)
의존성: pip install pillow opencv-python numpy
"""

import io
import os
from pathlib import Path
from PIL import Image
import numpy as np
import cv2


class CDRSanitizer:
    """
    5단계 무해화 체인
    ─────────────────
    Step 1: 메타데이터/EXIF 완전 제거       (외부 정보 차단)
    Step 2: 알파채널 제거                   (숨김 채널 차단)
    Step 3: 색공간 변환 RGB→YCbCr→RGB       (라운딩 손실로 LSB 깨짐)
    Step 4: 리사이즈 후 원복                (정보 손실 강제)
    Step 5: JPEG 재인코딩 (Q=85)            (LSB 비트 완전 파괴)
    """

    def __init__(self, jpeg_quality: int = 85, resize_ratio: float = 0.95):
        self.jpeg_quality = jpeg_quality
        self.resize_ratio = resize_ratio
        self.steps_log = []

    # ─────────────────────────────────────────────────
    # Step 1: 메타데이터/EXIF 제거
    # ─────────────────────────────────────────────────
    def step1_strip_metadata(self, img: Image.Image) -> Image.Image:
        """픽셀 데이터만 새 이미지로 복사 → EXIF/IPTC/XMP 모두 제거"""
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        self.steps_log.append("✓ Step 1: 메타데이터/EXIF 제거")
        return clean

    # ─────────────────────────────────────────────────
    # Step 2: 알파채널 제거
    # ─────────────────────────────────────────────────
    def step2_remove_alpha(self, img: Image.Image) -> Image.Image:
        """RGBA/LA/P 모드를 RGB로 변환 (알파채널은 LSB 은닉 통로)"""
        if img.mode == 'P':
            img = img.convert('RGBA')

        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            mask = img.split()[-1]
            background.paste(img.convert('RGB'), mask=mask)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        self.steps_log.append("✓ Step 2: 알파채널 제거")
        return img

    # ─────────────────────────────────────────────────
    # Step 3: 색공간 변환 (RGB ↔ YCbCr)
    # ─────────────────────────────────────────────────
    def step3_color_conversion(self, img: Image.Image) -> Image.Image:
        """RGB → YCbCr → RGB. 라운딩 손실로 LSB 단위 정보 파괴"""
        arr = np.array(img)
        ycbcr = cv2.cvtColor(arr, cv2.COLOR_RGB2YCrCb)
        rgb_back = cv2.cvtColor(ycbcr, cv2.COLOR_YCrCb2RGB)
        self.steps_log.append("✓ Step 3: 색공간 변환 (RGB→YCbCr→RGB)")
        return Image.fromarray(rgb_back)

    # ─────────────────────────────────────────────────
    # Step 4: 리사이즈 → 원복
    # ─────────────────────────────────────────────────
    def step4_resize_restore(self, img: Image.Image) -> Image.Image:
        """축소 후 다시 확대 → 보간(interpolation)으로 픽셀 재구성"""
        original_size = img.size
        small_size = (
            max(int(original_size[0] * self.resize_ratio), 1),
            max(int(original_size[1] * self.resize_ratio), 1),
        )
        small = img.resize(small_size, Image.LANCZOS)
        restored = small.resize(original_size, Image.LANCZOS)
        self.steps_log.append(
            f"✓ Step 4: 리사이즈 손실 ({int(self.resize_ratio*100)}%→100%)"
        )
        return restored

    # ─────────────────────────────────────────────────
    # Step 5: JPEG 재인코딩
    # ─────────────────────────────────────────────────
    def step5_jpeg_reencode(self, img: Image.Image) -> Image.Image:
        """무손실(PNG)→손실(JPEG) 변환으로 LSB 비트 완전 파괴"""
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=self.jpeg_quality, optimize=True)
        buffer.seek(0)
        reencoded = Image.open(buffer)
        reencoded.load()
        self.steps_log.append(f"✓ Step 5: JPEG 재인코딩 (Q={self.jpeg_quality})")
        return reencoded

    # ─────────────────────────────────────────────────
    # 전체 파이프라인 실행
    # ─────────────────────────────────────────────────
    def sanitize(self, input_path: str, output_path: str) -> dict:
        """5단계 체인을 순차 실행하고 결과 메트릭 반환"""
        self.steps_log = []

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"입력 파일 없음: {input_path}")

        original = Image.open(input_path)
        original_mode = original.mode
        original_size = original.size

        # 5단계 순차 실행
        img = self.step1_strip_metadata(original)
        img = self.step2_remove_alpha(img)
        img = self.step3_color_conversion(img)
        img = self.step4_resize_restore(img)
        img = self.step5_jpeg_reencode(img)

        # JPEG 강제 저장
        output_path = str(Path(output_path).with_suffix('.jpg'))
        img.save(output_path, format='JPEG', quality=self.jpeg_quality)

        # 픽셀 차이 계산 (시연용 메트릭)
        original_rgb = np.array(original.convert('RGB'))
        sanitized_rgb = np.array(Image.open(output_path).convert('RGB'))
        if original_rgb.shape == sanitized_rgb.shape:
            pixel_diff = float(np.mean(np.abs(
                original_rgb.astype(int) - sanitized_rgb.astype(int)
            )))
        else:
            pixel_diff = -1.0

        return {
            "status": "success",
            "input_path": input_path,
            "output_path": output_path,
            "original_mode": original_mode,
            "original_size": original_size,
            "original_kb": round(os.path.getsize(input_path) / 1024, 2),
            "sanitized_kb": round(os.path.getsize(output_path) / 1024, 2),
            "avg_pixel_diff": round(pixel_diff, 4),
            "steps_executed": self.steps_log.copy(),
        }


# ─────────────────────────────────────────────────
# 단독 실행 시 데모
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python cdr_sanitizer.py <입력이미지경로>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = "sanitized_output.jpg"

    sanitizer = CDRSanitizer(jpeg_quality=85, resize_ratio=0.95)
    result = sanitizer.sanitize(input_file, output_file)

    print("\n" + "=" * 60)
    print("  CDR 무해화 완료")
    print("=" * 60)
    for step in result["steps_executed"]:
        print(f"  {step}")
    print("-" * 60)
    print(f"  원본:  {result['original_kb']} KB")
    print(f"  결과:  {result['sanitized_kb']} KB → {result['output_path']}")
    print(f"  평균 픽셀 변화량: {result['avg_pixel_diff']}")
    print("=" * 60)
