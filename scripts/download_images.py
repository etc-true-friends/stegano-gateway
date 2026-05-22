"""
Unsplash 실제 사진 자동 다운로드 스크립트
==========================================
다양한 카테고리 사진 500장 자동 수집.
저작권 클린 (Unsplash License).

실행:
  python download_images.py
"""

import os
import time
import requests
from pathlib import Path

# ─────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────
ACCESS_KEY  = "AqxyVQzJ1nf3DGPBFAXwvPoV958eWOBo4WhNL1Z2SIM"
SAVE_DIR    = Path("real_images")
IMG_SIZE    = "regular"   # small / regular / full
PER_PAGE    = 30
TARGET      = 200         # 카테고리당 목표 장수

# 다양한 도메인 카테고리 (실제 시연 이미지와 유사)
CATEGORIES = [
    "nature landscape",
    "city street",
    "people portrait",
    "architecture building",
    "technology",
]

SAVE_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────
# 다운로드
# ─────────────────────────────────────────────────
def download_category(query: str, target: int) -> int:
    """카테고리별 이미지 다운로드"""
    folder = SAVE_DIR / query.replace(" ", "_")
    folder.mkdir(exist_ok=True)

    downloaded = 0
    page = 1

    while downloaded < target:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "page": page,
            "per_page": PER_PAGE,
            "orientation": "squarish",
        }
        headers = {"Authorization": f"Client-ID {ACCESS_KEY}"}

        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 401:
                print("  ERROR API 키 인증 실패")
                return downloaded
            if r.status_code == 403:
                print("  ERROR API 요청 한도 초과 (시간당 50회)")
                return downloaded

            data = r.json()
            results = data.get("results", [])

            if not results:
                break

            for photo in results:
                if downloaded >= target:
                    break

                img_url = photo["urls"][IMG_SIZE]
                img_id  = photo["id"]
                save_path = folder / f"{img_id}.jpg"

                if save_path.exists():
                    downloaded += 1
                    continue

                img_r = requests.get(img_url, timeout=15)
                if img_r.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(img_r.content)
                    downloaded += 1

                    if downloaded % 10 == 0:
                        print(f"    {query}: {downloaded}/{target}장")

                time.sleep(0.1)  # API 요청 제한 방지

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  WARN 오류: {e}")
            time.sleep(2)

    return downloaded


# ─────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────
print("=" * 60)
print("  Unsplash 실제 사진 다운로드")
print("=" * 60)

total = 0
for cat in CATEGORIES:
    print(f"\n▶ [{cat}] 다운로드 중...")
    count = download_category(cat, TARGET)
    total += count
    print(f"  → {count}장 완료")
    time.sleep(1)

# 결과 확인
all_files = list(SAVE_DIR.glob("**/*.jpg"))
print("\n" + "=" * 60)
print(f"  다운로드 완료! 총 {len(all_files)}장")
print(f"  저장 위치: {SAVE_DIR.absolute()}")
print("=" * 60)
print("\n  → 다음 단계: python build_dataset_real.py")
