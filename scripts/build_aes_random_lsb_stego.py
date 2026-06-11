import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile, PngImagePlugin

ImageFile.LOAD_TRUNCATED_IMAGES = True
PngImagePlugin.MAX_TEXT_CHUNK = 256 * 1024 * 1024
PngImagePlugin.MAX_TEXT_MEMORY = 512 * 1024 * 1024

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".pgm"}


def require_cryptography():
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        return Cipher, algorithms, modes, default_backend
    except ImportError as exc:
        raise SystemExit("cryptography 패키지가 필요합니다. 실행 전 pip install cryptography 를 설치하세요.") from exc


def list_images(path):
    path = Path(path)
    if not path.exists():
        return []
    return sorted([p for p in path.iterdir() if p.suffix.lower() in EXTS])


def load_rgb(path, size):
    with Image.open(path) as img:
        img = img.convert("RGB")
        if size > 0 and img.size != (size, size):
            w, h = img.size
            m = min(w, h)
            left = (w - m) // 2
            top = (h - m) // 2
            img = img.crop((left, top, left + m, top + m))
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return np.array(img, dtype=np.uint8)


def save_rgb(arr, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(
        path,
        format="PNG",
        optimize=False,
        compress_level=6,
    )


def aes_ctr_bytes(password, nonce, length):
    Cipher, algorithms, modes, default_backend = require_cryptography()
    key = hashlib.sha256(password.encode("utf-8")).digest()
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(b"\x00" * length) + encryptor.finalize()


def stable_u32(text):
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "little")


def choose_profile(rng, profile):
    if profile != "mixed":
        return profile
    return rng.choice(["weak", "balanced", "strong"], p=[0.50, 0.40, 0.10]).item()


def ratio_range_for_profile(profile):
    if profile == "weak":
        return 0.005, 0.015
    if profile == "balanced":
        return 0.020, 0.050
    if profile == "strong":
        return 0.060, 0.100
    raise ValueError(f"unknown profile: {profile}")


def select_channel_indices(height, width, channels):
    if channels == "rgb":
        return np.arange(height * width * 3, dtype=np.int64)

    channel_map = {"r": [0], "g": [1], "b": [2], "rg": [0, 1], "rb": [0, 2], "gb": [1, 2]}
    if channels not in channel_map:
        raise ValueError(f"unknown channels: {channels}")

    chs = np.array(channel_map[channels], dtype=np.int64)
    pixel_base = np.arange(height * width, dtype=np.int64) * 3
    return (pixel_base[:, None] + chs[None, :]).reshape(-1)


def embed_aes_random_lsb(rgb, password, payload_bytes, seed, channels="rgb"):
    arr = rgb.copy()
    h, w, _ = arr.shape
    flat = arr.reshape(-1)
    candidate_positions = select_channel_indices(h, w, channels)
    capacity_bits = len(candidate_positions)

    max_payload_bytes = max(1, capacity_bits // 8)
    payload_bytes = max(1, min(int(payload_bytes), max_payload_bytes))

    nonce = hashlib.md5(f"{password}:{seed}:{payload_bytes}:{channels}".encode("utf-8")).digest()
    encrypted = aes_ctr_bytes(password, nonce, payload_bytes)
    bits = np.unpackbits(np.frombuffer(encrypted, dtype=np.uint8))

    rng = np.random.default_rng(seed)
    positions = rng.choice(candidate_positions, size=len(bits), replace=False)
    flat[positions] = (flat[positions] & 0xFE) | bits
    return arr, int(len(bits)), int(capacity_bits)


def decide_payload_bytes(args, rng, used_profile, capacity_bits):
    capacity_bytes = max(1, capacity_bits // 8)

    if args.payload_bytes and args.payload_bytes > 0:
        return int(min(args.payload_bytes, capacity_bytes)), "fixed_bytes", 0.0

    if args.min_payload_bytes > 0 or args.max_payload_bytes > 0:
        low = args.min_payload_bytes if args.min_payload_bytes > 0 else 256
        high = args.max_payload_bytes if args.max_payload_bytes > 0 else max(low, 2048)
        if high < low:
            high = low
        payload_bytes = int(rng.integers(low, high + 1))
        return int(min(payload_bytes, capacity_bytes)), "custom_bytes", 0.0

    low_ratio, high_ratio = ratio_range_for_profile(used_profile)
    if args.min_embed_ratio > 0:
        low_ratio = float(args.min_embed_ratio)
    if args.max_embed_ratio > 0:
        high_ratio = float(args.max_embed_ratio)
    if high_ratio < low_ratio:
        high_ratio = low_ratio

    embed_ratio = float(rng.uniform(low_ratio, high_ratio))
    payload_bits = max(8, int(capacity_bits * embed_ratio))
    payload_bytes = max(1, payload_bits // 8)
    return int(min(payload_bytes, capacity_bytes)), "ratio", embed_ratio


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--stego_output_dir", default="")
    parser.add_argument("--cover_output_dir", default="")
    parser.add_argument("--size", type=int, default=256)

    parser.add_argument("--profile", choices=["weak", "balanced", "strong", "mixed"], default="mixed")
    parser.add_argument("--payload_bytes", type=int, default=0)
    parser.add_argument("--min_payload_bytes", type=int, default=0)
    parser.add_argument("--max_payload_bytes", type=int, default=0)
    parser.add_argument("--min_embed_ratio", type=float, default=0.0)
    parser.add_argument("--max_embed_ratio", type=float, default=0.0)
    parser.add_argument("--channels", choices=["r", "g", "b", "rg", "rb", "gb", "rgb"], default="rgb")

    parser.add_argument("--password", default="stegano-training")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log_csv", default="")
    parser.add_argument("--skip_bad", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    stego_output_dir = Path(args.stego_output_dir or args.output_dir or "dataset_aes_random_lsb/stego")
    cover_output_dir = Path(args.cover_output_dir) if args.cover_output_dir else None

    stego_output_dir.mkdir(parents=True, exist_ok=True)
    if cover_output_dir:
        cover_output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")

    images = list_images(input_dir)
    if not images:
        raise RuntimeError(f"no images found: {input_dir}")

    log_rows = []
    saved = 0
    skipped = 0

    for idx, path in enumerate(images):
        try:
            rgb = load_rgb(path, args.size)
            if cover_output_dir is not None:
                save_rgb(rgb, cover_output_dir / f"{path.stem}.png")
            image_seed = (int(args.seed) + idx + stable_u32(path.name)) & 0xFFFFFFFF
            rng = np.random.default_rng(image_seed)

            h, w, _ = rgb.shape
            capacity_bits = len(select_channel_indices(h, w, args.channels))
            used_profile = choose_profile(rng, args.profile)
            payload_bytes, payload_mode, target_ratio = decide_payload_bytes(args, rng, used_profile, capacity_bits)

            stego, used_bits, capacity = embed_aes_random_lsb(
                rgb=rgb,
                password=args.password,
                payload_bytes=payload_bytes,
                seed=image_seed,
                channels=args.channels,
            )

            out_name = f"{path.stem}.png"
            cover_path = ""
            if cover_output_dir:
                cover_path = str(cover_output_dir / out_name)
                save_rgb(rgb, cover_output_dir / out_name)

            stego_path = stego_output_dir / out_name
            save_rgb(stego, stego_path)
            saved += 1

            log_rows.append({
                "source": str(path),
                "cover_output": cover_path,
                "stego_output": str(stego_path),
                "profile": used_profile,
                "payload_mode": payload_mode,
                "payload_bytes": payload_bytes,
                "used_bits": used_bits,
                "capacity_bits": capacity,
                "target_embed_ratio": f"{target_ratio:.8f}",
                "actual_embed_ratio": f"{used_bits / max(capacity, 1):.8f}",
                "channels": args.channels,
                "seed": image_seed,
            })
        except Exception as exc:
            skipped += 1
            if args.skip_bad:
                print(f"[SKIP] {path} -> {exc}")
                continue
            raise

    if args.log_csv:
        log_path = Path(args.log_csv)
    else:
        log_path = stego_output_dir / "aes_random_lsb_metadata.csv"

    if log_rows:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
            writer.writeheader()
            writer.writerows(log_rows)

    if cover_output_dir:
        print(f"done: {saved} normalized cover images saved to {cover_output_dir}")
    print(f"done: {saved} AES random LSB stego images saved to {stego_output_dir}")
    print(f"metadata: {log_path}")
    if skipped:
        print(f"skipped: {skipped}")


if __name__ == "__main__":
    main()
