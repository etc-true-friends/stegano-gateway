import argparse
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image


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
    img = Image.open(path).convert("RGB")
    if size > 0:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    return np.array(img)


def save_rgb(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(path)


def aes_ctr_bytes(password, nonce, length):
    Cipher, algorithms, modes, default_backend = require_cryptography()
    key = hashlib.sha256(password.encode("utf-8")).digest()
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(b"\x00" * length) + encryptor.finalize()


def embed_aes_random_lsb(rgb, password, payload_bytes, seed):
    arr = rgb.copy()
    flat = arr.reshape(-1)
    capacity = len(flat)
    nonce = hashlib.md5(f"{password}:{seed}".encode("utf-8")).digest()
    encrypted = aes_ctr_bytes(password, nonce, payload_bytes)
    bits = np.unpackbits(np.frombuffer(encrypted, dtype=np.uint8))
    if len(bits) > capacity:
        bits = bits[:capacity]
    rng = np.random.default_rng(seed)
    positions = rng.choice(capacity, size=len(bits), replace=False)
    flat[positions] = (flat[positions] & 0xFE) | bits
    return arr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_aes_random_lsb/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--payload_bytes", type=int, default=2048)
    parser.add_argument("--password", default="stegano-training")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")

    images = list_images(input_dir)
    if not images:
        raise RuntimeError(f"no images found: {input_dir}")

    for idx, path in enumerate(images):
        rgb = load_rgb(path, args.size)
        stego = embed_aes_random_lsb(rgb, args.password, args.payload_bytes, args.seed + idx)
        save_rgb(stego, output_dir / f"{path.stem}.png")

    print(f"done: {len(images)} AES + random LSB stego images saved to {output_dir}")


if __name__ == "__main__":
    main()
