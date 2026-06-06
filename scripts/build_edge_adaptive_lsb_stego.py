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
import cv2

def embed_edge_adaptive_lsb(rgb, payload_ratio, channel, seed):
    rng = np.random.default_rng(seed)
    arr = rgb.copy()
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    t1 = int(rng.integers(40, 120))
    t2 = int(rng.integers(120, 220))
    edges = cv2.Canny(gray, t1, t2)
    ys, xs = np.where(edges > 0)
    if len(xs) == 0:
        return arr
    count = min(len(xs), max(1, int(len(xs) * payload_ratio)))
    selected = rng.choice(len(xs), size=count, replace=False)
    bits = rng.integers(0, 2, size=count, dtype=np.uint8)
    channels = rng.integers(0, 3, size=count) if channel == "random" else np.full(count, {"r": 0, "g": 1, "b": 2}[channel], dtype=np.int64)
    for j, bit in enumerate(bits):
        i = int(selected[j])
        arr[ys[i], xs[i], channels[j]] = (arr[ys[i], xs[i], channels[j]] & 0xFE) | bit
    return arr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_edge_adaptive_lsb/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--payload_ratio_min", type=float, default=0.05)
    parser.add_argument("--payload_ratio_max", type=float, default=0.60)
    parser.add_argument("--channel", default="random", choices=["r", "g", "b", "random"])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    images, output_dir = prepare_dirs(args.input_dir, args.output_dir)
    rng = np.random.default_rng(args.seed)
    ok = 0
    skipped = 0
    for idx, path in enumerate(images):
        try:
            payload_ratio = float(rng.uniform(args.payload_ratio_min, args.payload_ratio_max))
            rgb = load_rgb(path, args.size)
            stego = embed_edge_adaptive_lsb(rgb, payload_ratio, args.channel, args.seed + idx)
            save_rgb(stego, output_dir / f"{path.stem}.png")
            ok += 1
        except Exception as exc:
            skipped += 1
            print(f"[SKIP] {path.name}: {exc}")
    print(f"done: {ok} edge adaptive LSB stego images saved to {output_dir} / skipped: {skipped}")

if __name__ == "__main__":
    main()
