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

MID_FREQ = [(2, 3), (3, 2), (2, 4), (4, 2), (3, 3), (1, 4), (4, 1)]

def embed_dct_mid(rgb, strength, block_ratio, seed):
    rng = np.random.default_rng(seed)
    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycrcb[:, :, 0]
    h, w = y.shape
    h8 = h - (h % 8)
    w8 = w - (w % 8)
    coords = [(yy, xx) for yy in range(0, h8, 8) for xx in range(0, w8, 8)]
    if not coords:
        return rgb
    count = max(1, int(len(coords) * block_ratio))
    selected = rng.choice(len(coords), size=min(count, len(coords)), replace=False)
    out = y.copy()
    for idx in selected:
        yy, xx = coords[int(idx)]
        block = y[yy:yy + 8, xx:xx + 8] - 128.0
        dct = cv2.dct(block)
        u, v = MID_FREQ[int(rng.integers(0, len(MID_FREQ)))]
        bit = int(rng.integers(0, 2))
        delta = float(rng.uniform(0.5 * strength, 1.5 * strength))
        sign = 1.0 if bit else -1.0
        dct[u, v] = sign * (abs(dct[u, v]) + delta)
        out[yy:yy + 8, xx:xx + 8] = cv2.idct(dct) + 128.0
    ycrcb[:, :, 0] = np.clip(out, 0, 255)
    return cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2RGB)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_dct_mid/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--strength_min", type=float, default=1.0)
    parser.add_argument("--strength_max", type=float, default=8.0)
    parser.add_argument("--block_ratio_min", type=float, default=0.05)
    parser.add_argument("--block_ratio_max", type=float, default=0.40)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    images, output_dir = prepare_dirs(args.input_dir, args.output_dir)
    rng = np.random.default_rng(args.seed)
    ok = 0
    skipped = 0
    for idx, path in enumerate(images):
        try:
            strength = float(rng.uniform(args.strength_min, args.strength_max))
            block_ratio = float(rng.uniform(args.block_ratio_min, args.block_ratio_max))
            rgb = load_rgb(path, args.size)
            stego = embed_dct_mid(rgb, strength, block_ratio, args.seed + idx)
            save_rgb(stego, output_dir / f"{path.stem}.png")
            ok += 1
        except Exception as exc:
            skipped += 1
            print(f"[SKIP] {path.name}: {exc}")
    print(f"done: {ok} DCT mid stego images saved to {output_dir} / skipped: {skipped}")

if __name__ == "__main__":
    main()
