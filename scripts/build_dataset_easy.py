"""
커리큘럼 학습 1단계: 아주 쉬운(Easy) 데이터셋 생성
=====================================================
목적: SRNet이 LSB 노이즈의 기본 패턴을 쉽게 눈치채도록,
      사진 용량 한계치까지 메시지를 꽉꽉 채워 넣습니다.
"""

import random
import time
from pathlib import Path
from PIL import Image
from stegano import lsb as stegano_lsb

REAL_DIR     = Path("real_images")
DATASET_DIR  = Path("dataset_easy") # 폴더명 변경!
IMG_SIZE     = 256
TRAIN_RATIO  = 0.8
SEED         = 42
MAX_IMAGES   = 10000

# 256x256 RGB 사진의 LSB 최대 수용량은 약 24,000글자입니다.
# 꽉꽉 채워서 노이즈를 엄청나게 키웁니다! (약 0.9 bpp)
MASSIVE_PAYLOAD = "EASY_MODE_HACK_DETECT_TRAINING_" * 700 

random.seed(SEED)

for split in ["train", "val"]:
    for label in ["cover", "stego"]:
        (DATASET_DIR / split / label).mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("  Curriculum Learning: [Easy 난이도] 데이터셋 생성")
print("=" * 60)

all_files = list(REAL_DIR.glob("**/*.jpg"))
random.shuffle(all_files)
if len(all_files) > MAX_IMAGES:
    all_files = all_files[:MAX_IMAGES]

n_train = int(len(all_files) * TRAIN_RATIO)
train_files = all_files[:n_train]
val_files   = all_files[n_train:]

def process_split(files, split_name):
    cover_dir = DATASET_DIR / split_name / "cover"
    stego_dir = DATASET_DIR / split_name / "stego"
    success = 0
    t0 = time.time()

    for i, img_path in enumerate(files):
        try:
            img = Image.open(img_path).convert("RGB")
            w, h = img.size
            min_dim = min(w, h)
            left, top = (w - min_dim) // 2, (h - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))
            img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

            stem = f"{split_name}_{i:05d}"
            cover_path = cover_dir / f"{stem}.png"
            stego_path = stego_dir / f"{stem}.png"

            img.save(str(cover_path))
            # 무지막지하게 큰 페이로드 삽입!
            hidden = stegano_lsb.hide(str(cover_path), MASSIVE_PAYLOAD)
            hidden.save(str(stego_path))
            
            success += 1
            if (i + 1) % 500 == 0:
                print(f"  [{split_name}] {i+1}/{len(files)} 처리 완료")
        except:
            pass
    return success

print("▶ 학습(Train) 데이터 생성 중...")
process_split(train_files, "train")
print("\n▶ 검증(Val) 데이터 생성 중...")
process_split(val_files, "val")
print("\n  [Easy 난이도] 2만 샘플 데이터셋 완성! 🎉")