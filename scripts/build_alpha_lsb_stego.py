import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def list_images(path):
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    return sorted([p for p in Path(path).iterdir() if p.suffix.lower() in exts])


def load_rgba(path, size):
    img = Image.open(path).convert("RGBA")
    if size > 0:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    return np.array(img)


def save_rgba(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA").save(path)


def embed_alpha_lsb(rgba, payload_ratio, seed):
    rng = np.random.default_rng(seed)
    arr = rgba.copy()
    alpha = arr[:, :, 3].reshape(-1)
    count = min(len(alpha), max(1, int(len(alpha) * payload_ratio)))
    positions = rng.choice(len(alpha), size=count, replace=False)
    bits = rng.integers(0, 2, size=count, dtype=np.uint8)
    alpha[positions] = (alpha[positions] & 0xFE) | bits
    return arr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_alpha_lsb/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--payload_ratio", type=float, default=0.5)
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
        rgba = load_rgba(path, args.size)
        stego = embed_alpha_lsb(rgba, args.payload_ratio, args.seed + idx)
        save_rgba(stego, output_dir / f"{path.stem}.png")

    print(f"done: {len(images)} alpha-channel LSB stego images saved to {output_dir}")


if __name__ == "__main__":
    main()
