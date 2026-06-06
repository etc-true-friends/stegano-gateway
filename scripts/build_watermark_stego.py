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

def embed_spread_spectrum_watermark(rgb, strength, density, seed):
    rng = np.random.default_rng(seed)
    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
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
    parser.add_argument("--strength_min", type=float, default=0.5)
    parser.add_argument("--strength_max", type=float, default=4.0)
    parser.add_argument("--density_min", type=float, default=0.03)
    parser.add_argument("--density_max", type=float, default=0.30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    images, output_dir = prepare_dirs(args.input_dir, args.output_dir)
    rng = np.random.default_rng(args.seed)
    ok = 0
    skipped = 0
    for idx, path in enumerate(images):
        try:
            strength = float(rng.uniform(args.strength_min, args.strength_max))
            density = float(rng.uniform(args.density_min, args.density_max))
            rgb = load_rgb(path, args.size)
            stego = embed_spread_spectrum_watermark(rgb, strength, density, args.seed + idx)
            save_rgb(stego, output_dir / f"{path.stem}.png")
            ok += 1
        except Exception as exc:
            skipped += 1
            print(f"[SKIP] {path.name}: {exc}")
    print(f"done: {ok} watermark stego images saved to {output_dir} / skipped: {skipped}")

if __name__ == "__main__":
    main()
