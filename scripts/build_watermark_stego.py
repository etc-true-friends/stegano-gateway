import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


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


def embed_spread_spectrum_watermark(rgb, strength, density, seed):
    rng = np.random.default_rng(seed)
    arr = rgb.copy()
    ycrcb = cv2.cvtColor(arr, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycrcb[:, :, 0]
    mask = rng.random(y.shape) < density
    pattern = rng.choice([-strength, strength], size=y.shape)
    y[mask] += pattern[mask]
    ycrcb[:, :, 0] = np.clip(y, 0, 255)
    return cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_watermark/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--strength", type=float, default=2.0)
    parser.add_argument("--density", type=float, default=0.25)
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
        stego = embed_spread_spectrum_watermark(rgb, args.strength, args.density, args.seed + idx)
        save_rgb(stego, output_dir / f"{path.stem}.png")

    print(f"done: {len(images)} watermark-like stego images saved to {output_dir}")


if __name__ == "__main__":
    main()
