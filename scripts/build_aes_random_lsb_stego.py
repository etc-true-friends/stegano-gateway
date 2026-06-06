from pathlib import Path
from PIL import Image, ImageFile, PngImagePlugin
import numpy as np

ImageFile.LOAD_TRUNCATED_IMAGES = True
PngImagePlugin.MAX_TEXT_CHUNK = 1024 * 1024 * 1024
PngImagePlugin.MAX_TEXT_MEMORY = 1024 * 1024 * 1024

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

def list_images(path):
    return sorted([p for p in Path(path).iterdir() if p.suffix.lower() in EXTS])

def load_rgb(path, size):
    with Image.open(path) as img:
        img = img.convert("RGB")
        if size > 0:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return np.array(img)

def load_rgba(path, size):
    with Image.open(path) as img:
        img = img.convert("RGBA")
        if size > 0:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return np.array(img)

def save_rgb(arr, path):
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(path)

def save_rgba(arr, path):
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGBA").save(path)

def prepare_dirs(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")
    images = list_images(input_dir)
    if not images:
        raise RuntimeError(f"no images found: {input_dir}")
    return images, output_dir

import argparse
import hashlib

def require_cryptography():
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        return Cipher, algorithms, modes, default_backend
    except ImportError as exc:
        raise SystemExit("cryptography 패키지가 필요합니다. pip install cryptography") from exc

def aes_ctr_bytes(password, nonce, length):
    Cipher, algorithms, modes, default_backend = require_cryptography()
    key = hashlib.sha256(password.encode("utf-8")).digest()
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(b"\x00" * length) + encryptor.finalize()

def embed_aes_random_lsb(rgb, password, payload_ratio, channel_mode, seed):
    arr = rgb.copy()
    rng = np.random.default_rng(seed)
    if channel_mode == "random_one":
        c = int(rng.integers(0, 3))
        flat = arr[:, :, c].reshape(-1)
    else:
        flat = arr.reshape(-1)
    capacity = len(flat)
    bit_count = max(8, int(capacity * payload_ratio))
    payload_bytes = max(1, (bit_count + 7) // 8)
    nonce = hashlib.md5(f"{password}:{seed}".encode("utf-8")).digest()
    encrypted = aes_ctr_bytes(password, nonce, payload_bytes)
    bits = np.unpackbits(np.frombuffer(encrypted, dtype=np.uint8))[:bit_count]
    positions = rng.choice(capacity, size=len(bits), replace=False)
    flat[positions] = (flat[positions] & 0xFE) | bits
    return arr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_aes_random_lsb/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--payload_ratio_min", type=float, default=0.01)
    parser.add_argument("--payload_ratio_max", type=float, default=0.35)
    parser.add_argument("--channel_mode", default="mixed", choices=["mixed", "random_one"])
    parser.add_argument("--password", default="stegano-training")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    images, output_dir = prepare_dirs(args.input_dir, args.output_dir)
    rng = np.random.default_rng(args.seed)
    ok = 0
    skipped = 0
    for idx, path in enumerate(images):
        try:
            payload_ratio = float(rng.uniform(args.payload_ratio_min, args.payload_ratio_max))
            channel_mode = args.channel_mode if args.channel_mode != "mixed" else ("random_one" if rng.random() < 0.5 else "mixed")
            rgb = load_rgb(path, args.size)
            stego = embed_aes_random_lsb(rgb, args.password, payload_ratio, channel_mode, args.seed + idx)
            save_rgb(stego, output_dir / f"{path.stem}.png")
            ok += 1
        except Exception as exc:
            skipped += 1
            print(f"[SKIP] {path.name}: {exc}")
    print(f"done: {ok} AES random LSB stego images saved to {output_dir} / skipped: {skipped}")

if __name__ == "__main__":
    main()
