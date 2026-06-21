import os
import csv
import json
import math
import random
import hashlib
import argparse
from datetime import datetime

import numpy as np
from PIL import Image, ImageFile

try:
    from Crypto.Cipher import AES
except ImportError:
    raise ImportError(
        "pycryptodome package is required. Install with: pip install pycryptodome"
    )

ImageFile.LOAD_TRUNCATED_IMAGES = True

# -------------------------------------------------------------------
# 1. Paths
# -------------------------------------------------------------------
WORKSPACE_DIR = "D:/final_project/4_Local_Workspace"
RAW_POOL_DIR = f"{WORKSPACE_DIR}/real_images"

OUTPUT_DIR = f"{WORKSPACE_DIR}/dataset_aes_random_lsb"
TRAIN_COVER = f"{OUTPUT_DIR}/train/cover"
TRAIN_STEGO = f"{OUTPUT_DIR}/train/stego"
VAL_COVER = f"{OUTPUT_DIR}/val/cover"
VAL_STEGO = f"{OUTPUT_DIR}/val/stego"

MANIFEST_PATH = f"{OUTPUT_DIR}/manifest.csv"
SUMMARY_PATH = f"{OUTPUT_DIR}/dataset_summary.json"

# -------------------------------------------------------------------
# 2. Experiment settings
# -------------------------------------------------------------------
METHOD_NAME = "aes_random_lsb"
SEED = 42
TRAIN_RATIO = 0.8
IMAGE_SIZE = (256, 256)
PAYLOAD_BPP = 0.4

# Set True when rebuilding the same dataset folder from scratch.
CLEAR_EXISTING_OUTPUT_IMAGES = True

AES_KEY = hashlib.sha256(b"srnet-aes-random-lsb-fixed-key").digest()[:16]
VALID_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


def apply_cli_args():
    """Apply command-line overrides for small diagnostic dataset builds."""
    global OUTPUT_DIR, TRAIN_COVER, TRAIN_STEGO, VAL_COVER, VAL_STEGO
    global MANIFEST_PATH, SUMMARY_PATH, PAYLOAD_BPP, CLEAR_EXISTING_OUTPUT_IMAGES

    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default=OUTPUT_DIR)
    parser.add_argument("--payload_bpp", type=float, default=PAYLOAD_BPP)
    parser.add_argument("--max_images", type=int, default=None)
    parser.add_argument("--no_clear", action="store_true")
    args = parser.parse_args()

    OUTPUT_DIR = args.output_dir.replace("\\", "/")
    TRAIN_COVER = f"{OUTPUT_DIR}/train/cover"
    TRAIN_STEGO = f"{OUTPUT_DIR}/train/stego"
    VAL_COVER = f"{OUTPUT_DIR}/val/cover"
    VAL_STEGO = f"{OUTPUT_DIR}/val/stego"
    MANIFEST_PATH = f"{OUTPUT_DIR}/manifest.csv"
    SUMMARY_PATH = f"{OUTPUT_DIR}/dataset_summary.json"
    PAYLOAD_BPP = args.payload_bpp
    CLEAR_EXISTING_OUTPUT_IMAGES = not args.no_clear

    return args


# -------------------------------------------------------------------
# 3. Directory and cleanup helpers
# -------------------------------------------------------------------
def create_directories():
    for d in [TRAIN_COVER, TRAIN_STEGO, VAL_COVER, VAL_STEGO]:
        os.makedirs(d, exist_ok=True)


def clear_output_images():
    if not CLEAR_EXISTING_OUTPUT_IMAGES:
        return 0

    removed = 0
    for d in [TRAIN_COVER, TRAIN_STEGO, VAL_COVER, VAL_STEGO]:
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if name.lower().endswith((".png", ".jpg", ".jpeg")):
                os.remove(os.path.join(d, name))
                removed += 1
    return removed


# -------------------------------------------------------------------
# 4. Source image collection
# -------------------------------------------------------------------
def collect_images():
    raw_images = []

    for root, _, files in os.walk(RAW_POOL_DIR):
        for file in files:
            if file.lower().endswith(VALID_EXTENSIONS):
                raw_images.append(os.path.join(root, file).replace("\\", "/"))

    return sorted(set(raw_images), key=lambda p: p.lower())


# -------------------------------------------------------------------
# 5. AES + Random LSB helpers
# -------------------------------------------------------------------
def stable_seed(src_path):
    text = f"{SEED}|{src_path.lower()}"
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32)


def make_nonce(src_path):
    digest = hashlib.sha256(src_path.lower().encode("utf-8")).digest()
    return digest[:8]


def aes_encrypt_bits(src_path, bit_count):
    byte_count = math.ceil(bit_count / 8)
    rng = np.random.default_rng(stable_seed(src_path))

    plaintext = rng.integers(0, 256, size=byte_count, dtype=np.uint8).tobytes()
    cipher = AES.new(AES_KEY, AES.MODE_CTR, nonce=make_nonce(src_path))
    ciphertext = cipher.encrypt(plaintext)

    bits = np.unpackbits(np.frombuffer(ciphertext, dtype=np.uint8))
    return bits[:bit_count].astype(np.uint8), rng


# -------------------------------------------------------------------
# 6. Stego generation
# -------------------------------------------------------------------
def build_stego_array(cover_arr, src_path):
    height, width, channels = cover_arr.shape
    flat = cover_arr.reshape(-1)
    max_capacity = flat.size

    # Paper-style bpp: bits per pixel, not RGB-channel ratio.
    embed_bits_count = int(height * width * PAYLOAD_BPP)

    if embed_bits_count <= 0:
        raise ValueError("PAYLOAD_BPP is too low; embed bit count became 0.")

    if embed_bits_count > max_capacity:
        raise ValueError(
            f"PAYLOAD_BPP={PAYLOAD_BPP} is too high. "
            f"required_bits={embed_bits_count}, max_capacity={max_capacity}"
        )

    payload_bits, rng = aes_encrypt_bits(src_path, embed_bits_count)
    positions = rng.choice(max_capacity, size=embed_bits_count, replace=False)

    stego_flat = flat.copy()
    stego_flat[positions] = (stego_flat[positions] & 254) | payload_bits

    return stego_flat.reshape(cover_arr.shape).astype(np.uint8), embed_bits_count


def process_image_pair(src_path, target_cover_path, target_stego_path):
    try:
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            if IMAGE_SIZE is not None:
                img = img.resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
            cover_arr = np.array(img, dtype=np.uint8)

        stego_arr, embed_bits_count = build_stego_array(cover_arr, src_path)

        Image.fromarray(cover_arr, mode="RGB").save(target_cover_path, format="PNG")
        Image.fromarray(stego_arr, mode="RGB").save(target_stego_path, format="PNG")

        return True, embed_bits_count, ""

    except Exception as e:
        if os.path.exists(target_cover_path):
            os.remove(target_cover_path)
        if os.path.exists(target_stego_path):
            os.remove(target_stego_path)
        return False, 0, str(e)


def count_pngs(path):
    if not os.path.isdir(path):
        return 0
    return len([f for f in os.listdir(path) if f.lower().endswith(".png")])


def write_summary(start_time, end_time, total_imgs, success_count, fail_count, removed_count):
    summary = {
        "method": METHOD_NAME,
        "payload_bpp": PAYLOAD_BPP,
        "image_size": IMAGE_SIZE,
        "seed": SEED,
        "train_ratio": TRAIN_RATIO,
        "aes_mode": "CTR",
        "random_lsb_positioning": True,
        "source_dir": RAW_POOL_DIR,
        "output_dir": OUTPUT_DIR,
        "started_at": start_time.isoformat(timespec="seconds"),
        "finished_at": end_time.isoformat(timespec="seconds"),
        "elapsed_seconds": round((end_time - start_time).total_seconds(), 2),
        "total_source_images": total_imgs,
        "success_pairs": success_count,
        "failed_images": fail_count,
        "removed_existing_output_images": removed_count,
        "train_cover_count": count_pngs(TRAIN_COVER),
        "train_stego_count": count_pngs(TRAIN_STEGO),
        "val_cover_count": count_pngs(VAL_COVER),
        "val_stego_count": count_pngs(VAL_STEGO),
        "manifest_path": MANIFEST_PATH,
    }

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


# -------------------------------------------------------------------
# 7. Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    args = apply_cli_args()
    start_time = datetime.now()
    random.seed(SEED)
    np.random.seed(SEED)

    create_directories()
    removed_count = clear_output_images()

    print(f"[*] Source image directory: {RAW_POOL_DIR}")
    print(f"[*] Output directory: {OUTPUT_DIR}")
    if removed_count:
        print(f"[*] Removed existing output images: {removed_count}")

    raw_images = collect_images()
    if not raw_images:
        print(f"[!] No source images found in: {RAW_POOL_DIR}")
        raise SystemExit(1)

    random.shuffle(raw_images)
    if args.max_images is not None:
        raw_images = raw_images[:args.max_images]

    total_imgs = len(raw_images)
    split_idx = int(total_imgs * TRAIN_RATIO)
    train_set = raw_images[:split_idx]
    val_set = raw_images[split_idx:]

    print(f"[+] Source images: {total_imgs}")
    print(f"[+] Train pairs planned: {len(train_set)}")
    print(f"[+] Validation pairs planned: {len(val_set)}")
    print(f"[+] Image size: {IMAGE_SIZE}")
    print(f"[+] Payload: {PAYLOAD_BPP} bpp")
    print()

    success_count = 0
    fail_count = 0

    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "method",
            "payload_bpp",
            "mode",
            "index",
            "source_path",
            "cover_path",
            "stego_path",
            "success",
            "embed_bits",
            "error",
        ])

        for mode, dataset in [("train", train_set), ("val", val_set)]:
            cover_dir = TRAIN_COVER if mode == "train" else VAL_COVER
            stego_dir = TRAIN_STEGO if mode == "train" else VAL_STEGO

            for idx, src_path in enumerate(dataset):
                filename = f"img_{idx:08d}.png"
                target_cover = os.path.join(cover_dir, filename)
                target_stego = os.path.join(stego_dir, filename)

                success, embed_bits, error = process_image_pair(
                    src_path,
                    target_cover,
                    target_stego,
                )

                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"\n[!] Failed: {os.path.basename(src_path)} - {error}")

                writer.writerow([
                    METHOD_NAME,
                    PAYLOAD_BPP,
                    mode,
                    idx,
                    src_path,
                    target_cover.replace("\\", "/"),
                    target_stego.replace("\\", "/"),
                    success,
                    embed_bits,
                    error,
                ])

                if (idx + 1) % 100 == 0 or (idx + 1) == len(dataset):
                    print(
                        f"\r  -> [{mode.upper():>5}] {idx + 1}/{len(dataset)} pairs processed",
                        end="",
                    )

            print()

    end_time = datetime.now()
    summary = write_summary(
        start_time=start_time,
        end_time=end_time,
        total_imgs=total_imgs,
        success_count=success_count,
        fail_count=fail_count,
        removed_count=removed_count,
    )

    print()
    print("[*] AES + Random LSB dataset build complete")
    print(f"[+] Success pairs: {summary['success_pairs']}")
    print(f"[+] Failed images: {summary['failed_images']}")
    print(f"[+] Train cover/stego: {summary['train_cover_count']} / {summary['train_stego_count']}")
    print(f"[+] Val cover/stego: {summary['val_cover_count']} / {summary['val_stego_count']}")
    print(f"[+] Manifest: {MANIFEST_PATH}")
    print(f"[+] Summary: {SUMMARY_PATH}")
