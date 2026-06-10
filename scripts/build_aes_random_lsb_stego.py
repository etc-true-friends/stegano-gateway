import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile, PngImagePlugin

ImageFile.LOAD_TRUNCATED_IMAGES = True
PngImagePlugin.MAX_TEXT_CHUNK = 256 * 1024 * 1024
PngImagePlugin.MAX_TEXT_MEMORY = 512 * 1024 * 1024


def require_cryptography():
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        return Cipher, algorithms, modes, default_backend
    except ImportError as exc:
        raise SystemExit("cryptography 패키지가 필요합니다. 실행 전 pip install cryptography 를 설치하세요.") from exc


def list_images(path):
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    return sorted([p for p in Path(path).iterdir() if p.suffix.lower() in exts])


def load_rgb(path, size):
    with Image.open(path) as img:
        img = img.convert("RGB")
        if size > 0:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return np.array(img, dtype=np.uint8)


def save_rgb(arr, path):
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
    return rng.choice(["weak", "balanced", "strong"], p=[0.15, 0.55, 0.30]).item()


def payload_range_for_profile(profile):
    if profile == "weak":
        return 2048, 4096
    if profile == "balanced":
        return 4096, 8192
    if profile == "strong":
        return 8192, 12288
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
    capacity = len(candidate_positions)

    max_payload_bytes = capacity // 8
    payload_bytes = max(1, min(int(payload_bytes), max_payload_bytes))

    nonce = hashlib.md5(f"{password}:{seed}:{payload_bytes}:{channels}".encode("utf-8")).digest()
    encrypted = aes_ctr_bytes(password, nonce, payload_bytes)
    bits = np.unpackbits(np.frombuffer(encrypted, dtype=np.uint8))

    rng = np.random.default_rng(seed)
    positions = rng.choice(candidate_positions, size=len(bits), replace=False)
    flat[positions] = (flat[positions] & 0xFE) | bits
    return arr, int(len(bits)), int(capacity)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_aes_random_lsb/stego")
    parser.add_argument("--size", type=int, default=256)

    parser.add_argument("--profile", choices=["weak", "balanced", "strong", "mixed"], default="mixed")
    parser.add_argument("--payload_bytes", type=int, default=0)
    parser.add_argument("--min_payload_bytes", type=int, default=0)
    parser.add_argument("--max_payload_bytes", type=int, default=0)
    parser.add_argument("--channels", choices=["r", "g", "b", "rg", "rb", "gb", "rgb"], default="rgb")

    parser.add_argument("--password", default="stegano-training")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log_csv", default="")
    parser.add_argument("--skip_bad", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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
            image_seed = (int(args.seed) + idx + stable_u32(path.name)) & 0xFFFFFFFF
            rng = np.random.default_rng(image_seed)

            if args.payload_bytes and args.payload_bytes > 0:
                used_profile = "fixed"
                payload_bytes = int(args.payload_bytes)
            else:
                used_profile = choose_profile(rng, args.profile)
                low, high = payload_range_for_profile(used_profile)
                if args.min_payload_bytes > 0:
                    low = int(args.min_payload_bytes)
                if args.max_payload_bytes > 0:
                    high = int(args.max_payload_bytes)
                if high < low:
                    high = low
                payload_bytes = int(rng.integers(low, high + 1))

            stego, used_bits, capacity = embed_aes_random_lsb(
                rgb=rgb,
                password=args.password,
                payload_bytes=payload_bytes,
                seed=image_seed,
                channels=args.channels,
            )
            out_path = output_dir / f"{path.stem}.png"
            save_rgb(stego, out_path)
            saved += 1

            log_rows.append({
                "source": str(path),
                "output": str(out_path),
                "profile": used_profile,
                "payload_bytes": payload_bytes,
                "used_bits": used_bits,
                "capacity_bits": capacity,
                "embed_ratio": f"{used_bits / max(capacity, 1):.8f}",
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
        log_path = output_dir / "aes_random_lsb_metadata.csv"

    if log_rows:
        with log_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
            writer.writeheader()
            writer.writerows(log_rows)

    print(f"done: {saved} AES random LSB stego images saved to {output_dir}")
    print(f"metadata: {log_path}")
    if skipped:
        print(f"skipped: {skipped}")


if __name__ == "__main__":
    main()
