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


def texture_mask(rgb, percentile):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    mean = cv2.blur(gray, (7, 7))
    mean_sq = cv2.blur(gray * gray, (7, 7))
    variance = mean_sq - mean * mean
    threshold = np.percentile(variance, percentile)
    return variance >= threshold


def embed_texture_adaptive_lsb(rgb, payload_ratio, percentile, channel, seed):
    rng = np.random.default_rng(seed)
    arr = rgb.copy()
    ys, xs = np.where(texture_mask(arr, percentile))
    if len(xs) == 0:
        return arr

    count = min(len(xs), max(1, int(len(xs) * payload_ratio)))
    selected = rng.choice(len(xs), size=count, replace=False)
    bits = rng.integers(0, 2, size=count, dtype=np.uint8)

    if channel == "random":
        channels = rng.integers(0, 3, size=count)
    else:
        channels = np.full(count, {"r": 0, "g": 1, "b": 2}[channel.lower()], dtype=np.int64)

    for j, bit in enumerate(bits):
        i = selected[j]
        arr[ys[i], xs[i], channels[j]] = (arr[ys[i], xs[i], channels[j]] & 0xFE) | bit
    return arr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_texture_adaptive_lsb/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--payload_ratio", type=float, default=0.6)
    parser.add_argument("--percentile", type=float, default=65.0)
    parser.add_argument("--channel", default="random", choices=["r", "g", "b", "random"])
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
        stego = embed_texture_adaptive_lsb(rgb, args.payload_ratio, args.percentile, args.channel, args.seed + idx)
        save_rgb(stego, output_dir / f"{path.stem}.png")

    print(f"done: {len(images)} texture adaptive LSB stego images saved to {output_dir}")


if __name__ == "__main__":
    main()
