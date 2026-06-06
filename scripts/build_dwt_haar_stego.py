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

def haar2d(x):
    h, w = x.shape
    h2 = h - (h % 2)
    w2 = w - (w % 2)
    x = x[:h2, :w2]
    a = x[0::2, 0::2]
    b = x[0::2, 1::2]
    c = x[1::2, 0::2]
    d = x[1::2, 1::2]
    ll = (a + b + c + d) / 4.0
    lh = (a - b + c - d) / 4.0
    hl = (a + b - c - d) / 4.0
    hh = (a - b - c + d) / 4.0
    return ll, lh, hl, hh, h2, w2

def ihaar2d(ll, lh, hl, hh, h, w):
    a = ll + lh + hl + hh
    b = ll - lh + hl - hh
    c = ll + lh - hl - hh
    d = ll - lh - hl + hh
    out = np.zeros((h, w), dtype=np.float32)
    out[0::2, 0::2] = a
    out[0::2, 1::2] = b
    out[1::2, 0::2] = c
    out[1::2, 1::2] = d
    return out

def perturb_band(band, rng, strength, coeff_ratio):
    flat = band.reshape(-1)
    count = max(1, int(len(flat) * coeff_ratio))
    pos = rng.choice(len(flat), size=min(count, len(flat)), replace=False)
    flat[pos] += rng.choice([-strength, strength], size=len(pos))

def embed_dwt_haar(rgb, strength, coeff_ratio, bands, seed):
    rng = np.random.default_rng(seed)
    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycrcb[:, :, 0]
    ll, lh, hl, hh, h, w = haar2d(y)
    targets = []
    if "LH" in bands:
        targets.append(lh)
    if "HL" in bands:
        targets.append(hl)
    if "HH" in bands:
        targets.append(hh)
    if not targets:
        targets = [hh]
    for band in targets:
        perturb_band(band, rng, strength, coeff_ratio)
    y2 = y.copy()
    y2[:h, :w] = ihaar2d(ll, lh, hl, hh, h, w)
    ycrcb[:, :, 0] = np.clip(y2, 0, 255)
    return cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2RGB)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_dwt_haar/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--strength_min", type=float, default=0.5)
    parser.add_argument("--strength_max", type=float, default=6.0)
    parser.add_argument("--coeff_ratio_min", type=float, default=0.03)
    parser.add_argument("--coeff_ratio_max", type=float, default=0.35)
    parser.add_argument("--bands", default="random", help="random or comma list: LH,HL,HH")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    images, output_dir = prepare_dirs(args.input_dir, args.output_dir)
    rng = np.random.default_rng(args.seed)
    choices = [["LH"], ["HL"], ["HH"], ["LH", "HL"], ["HL", "HH"], ["LH", "HH"], ["LH", "HL", "HH"]]
    fixed_bands = None if args.bands.lower() == "random" else [b.strip().upper() for b in args.bands.split(",") if b.strip()]
    ok = 0
    skipped = 0
    for idx, path in enumerate(images):
        try:
            strength = float(rng.uniform(args.strength_min, args.strength_max))
            coeff_ratio = float(rng.uniform(args.coeff_ratio_min, args.coeff_ratio_max))
            bands = fixed_bands if fixed_bands is not None else choices[int(rng.integers(0, len(choices)))]
            rgb = load_rgb(path, args.size)
            stego = embed_dwt_haar(rgb, strength, coeff_ratio, bands, args.seed + idx)
            save_rgb(stego, output_dir / f"{path.stem}.png")
            ok += 1
        except Exception as exc:
            skipped += 1
            print(f"[SKIP] {path.name}: {exc}")
    print(f"done: {ok} DWT Haar stego images saved to {output_dir} / skipped: {skipped}")

if __name__ == "__main__":
    main()
