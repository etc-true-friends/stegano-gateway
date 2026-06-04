"""
Dataset Generation Script for Steganalysis (Real-world Image Domain)

Description:
  Generates cover and stego image pairs from a raw image directory.
  Implements random payload sizes to ensure variance in steganographic noise.
  Includes strict memory management, file handle release mechanisms, 
  and a Resume (Checkpoint) feature to continue from the last failure point.
"""

import gc
import logging
import random
import string  # 랜덤 문자열 생성을 위해 추가
import time
import traceback
from pathlib import Path

from PIL import Image
from stegano import lsb as stegano_lsb

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
REAL_DIR     = Path(r"real_images")
DATASET_DIR  = Path(r"dataset_real")
IMG_SIZE     = 256
TRAIN_RATIO  = 0.8
SEED         = 42
MAX_IMAGES   = 230000

# [수정됨] 고정된 리스트 대신 랜덤 문자열 생성 함수로 교체하여 과적합 원천 차단
def get_random_payload(min_len=3000, max_len=8000):
    """지정된 범위 내에서 무작위 길이의 랜덤 문자열을 생성하여 은닉 패턴의 불규칙성 보장"""
    length = random.randint(min_len, max_len)
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

# ---------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def setup_directories() -> None:
    for split in ["train", "val"]:
        for label in ["cover", "stego"]:
            (DATASET_DIR / split / label).mkdir(parents=True, exist_ok=True)

def process_split(files: list, split_name: str) -> tuple:
    cover_dir = DATASET_DIR / split_name / "cover"
    stego_dir = DATASET_DIR / split_name / "stego"
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    total_files = len(files)
    
    start_time = time.time()

    for i, img_path in enumerate(files):
        stem = f"{split_name}_{i:06d}"
        cover_path = cover_dir / f"{stem}.png"
        stego_path = stego_dir / f"{stem}.png"

        # [핵심 로직] 재시작(Resume) 지원: 이미 생성된 파일이 있다면 건너뜀
        if cover_path.exists() and stego_path.exists():
            skip_count += 1
            if (i + 1) % 500 == 0 or (i + 1) == total_files:
                logging.info(f"[{split_name.upper()}] {i+1}/{total_files} skipped (already exists).")
            continue

        img_original = None
        img_cropped = None
        img_resized = None
        hidden_img = None
        
        try:
            img_original = Image.open(img_path).convert("RGB")
            w, h = img_original.size
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top  = (h - min_dim) // 2
            
            img_cropped = img_original.crop((left, top, left + min_dim, top + min_dim))
            img_resized = img_cropped.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

            img_resized.save(str(cover_path), format="PNG")

            # [수정됨] 매번 완전히 다른 랜덤 쓰레기값을 생성하여 삽입
            secret = get_random_payload()
            hidden_img = stegano_lsb.hide(str(cover_path), secret)
            hidden_img.save(str(stego_path), format="PNG")

            success_count += 1

            if (i + 1) % 500 == 0 or (i + 1) == total_files:
                elapsed = time.time() - start_time
                processed_so_far = success_count + fail_count
                if processed_so_far > 0:
                    eta_seconds = (elapsed / processed_so_far) * (total_files - (i + 1))
                    logging.info(f"[{split_name.upper()}] {i+1}/{total_files} processed. "
                                 f"ETA: {eta_seconds/60:.1f} mins")
                gc.collect()

        except Exception as e:
            fail_count += 1
            if fail_count <= 10:
                logging.warning(f"Failed to process {img_path.name}: {e}")
                
        finally:
            if img_original:
                img_original.close()
            if img_cropped:
                img_cropped.close()
            if img_resized:
                img_resized.close()
            if hidden_img and hasattr(hidden_img, 'close'):
                hidden_img.close()

    logging.info(f"[{split_name.upper()}] Result -> Success: {success_count}, Skipped: {skip_count}, Failed: {fail_count}")
    return success_count, skip_count, fail_count

def main():
    random.seed(SEED)
    setup_directories()

    logging.info("Starting dataset generation process (with Resume support).")
    
    all_files = list(REAL_DIR.glob("**/*.jpg")) + list(REAL_DIR.glob("**/*.png"))
    total_collected = len(all_files)
    logging.info(f"Total raw images found: {total_collected}")

    if total_collected < 100:
        logging.error("Insufficient images. Aborting process.")
        return

    random.shuffle(all_files)
    
    if total_collected > MAX_IMAGES:
        all_files = all_files[:MAX_IMAGES]
        logging.info(f"Limiting dataset to {MAX_IMAGES} images.")

    n_train = int(len(all_files) * TRAIN_RATIO)
    train_files = all_files[:n_train]
    val_files   = all_files[n_train:]

    logging.info(f"Split ratio -> Train: {len(train_files)}, Val: {len(val_files)}")

    logging.info("Processing training dataset...")
    tr_success, tr_skip, tr_fail = process_split(train_files, "train")

    logging.info("Processing validation dataset...")
    va_success, va_skip, va_fail = process_split(val_files, "val")

    total_created = tr_success + va_success
    total_retained = tr_skip + va_skip
    logging.info(f"Dataset generation finished.")
    logging.info(f"Newly created pairs: {total_created}, Retained pairs: {total_retained}")
    logging.info("Next step: Execute 'python train.py'")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error("🚨치명적인 에러로 프로세스가 중단되었습니다 🚨")
        logging.error(traceback.format_exc())
    except KeyboardInterrupt:
        logging.warning("사용자에 의해 강제 중단(Ctrl+C) 되었습니다.")
