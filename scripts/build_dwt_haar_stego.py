import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFile, PngImagePlugin

ImageFile.LOAD_TRUNCATED_IMAGES = True
PngImagePlugin.MAX_TEXT_CHUNK = 1024 * 1024 * 1024
PngImagePlugin.MAX_TEXT_MEMORY = 1024 * 1024 * 1024

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def list_images(path):
    return sorted([p for p in Path(path).iterdir() if p.suffix.lower() in EXTS])


def parse_range(value, default_low, default_high):
    if value is None:
        return default_low, default_high
    value = str(value).strip()
    if "," in value:
        a, b = value.split(",", 1)
        return float(a), float(b)
    v = float(value)
    return v, v


def load_rgb(path, size):
    with Image.open(path) as img:
        img = img.convert("RGB")
        if size > 0:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return np.array(img)


def save_rgb(arr, path):
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(path, format="PNG", optimize=False)


def haar2d(x):
    h, w = x.shape
    h2 = h - (h % 2)
    w2 = w - (w % 2)
    x = x[:h2, :w2]
    a = x[0::2, 0::2]
    b = x[0::2, 1::2]
    c = x[1::2, 0::2]
    d = x[1::2, 1::2]
    ll = (a + b + c + d) * 0.25
    lh = (a - b + c - d) * 0.25
    hl = (a + b - c - d) * 0.25
    hh = (a - b - c + d) * 0.25
    return ll, lh, hl, hh, h2, w2


def ihaar2d(ll, lh, hl, hh, h, w):
    a = ll + lh + hl + hh
    b = ll - lh + hl - hh
    c = ll + lh - hl + hh
    d = ll - lh - hl - hh
    out = np.zeros((h, w), dtype=np.float32)
    out[0::2, 0::2] = a
    out[0::2, 1::2] = b
    out[1::2, 0::2] = c
    out[1::2, 1::2] = d
    return out


def band_candidates(band, low_percentile, high_percentile):
    mag = np.abs(band).reshape(-1)
    if mag.size == 0:
        return np.array([], dtype=np.int64)
    lo = np.percentile(mag, low_percentile)
    hi = np.percentile(mag, high_percentile)
    idx = np.flatnonzero((mag >= lo) & (mag <= hi))
    if idx.size == 0:
        idx = np.flatnonzero(mag >= lo)
    if idx.size == 0:
        idx = np.arange(mag.size)
    return idx


def choose_profile(profile, rng):
    if profile == "ultra":
        bands = [("HH",), ("LH",), ("HL",)][rng.integers(0, 3)]
        return rng.uniform(0.03, 0.18), rng.uniform(0.0002, 0.0025), rng.uniform(75.0, 92.0), rng.uniform(92.0, 99.5), bands
    if profile == "weak":
        bands = [("HH",), ("LH",), ("HL",), ("LH", "HL")][rng.integers(0, 4)]
        return rng.uniform(0.06, 0.35), rng.uniform(0.0005, 0.006), rng.uniform(70.0, 90.0), rng.uniform(90.0, 99.0), bands
    if profile == "balanced":
        bands = [("LH",), ("HL",), ("HH",), ("LH", "HL"), ("HL", "HH")][rng.integers(0, 5)]
        return rng.uniform(0.15, 0.65), rng.uniform(0.002, 0.012), rng.uniform(60.0, 85.0), rng.uniform(88.0, 98.0), bands
    if profile == "hard":
        bands = [("LH", "HL"), ("LH", "HH"), ("HL", "HH"), ("LH", "HL", "HH")][rng.integers(0, 4)]
        return rng.uniform(0.45, 1.20), rng.uniform(0.008, 0.025), rng.uniform(50.0, 80.0), rng.uniform(85.0, 97.0), bands
    if profile == "mixed":
        r = rng.random()
        if r < 0.70:
            return choose_profile("ultra", rng)
        if r < 0.95:
            return choose_profile("weak", rng)
        return choose_profile("balanced", rng)
    raise ValueError(f"unknown profile: {profile}")


def modify_band(band, ratio, strength, low_percentile, high_percentile, rng):
    flat = band.reshape(-1)
    candidates = band_candidates(band, low_percentile, high_percentile)
    count = max(1, int(candidates.size * ratio))
    count = min(count, candidates.size)
    selected = rng.choice(candidates, size=count, replace=False)
    signs = rng.choice([-1.0, 1.0], size=count).astype(np.float32)
    jitter = rng.uniform(0.55, 1.15, size=count).astype(np.float32)
    original = flat[selected].copy()
    flat[selected] = original + signs * strength * jitter
    return band


def embed_dwt_haar(rgb, profile, strength_range, ratio_range, low_range, high_range, seed, bands_arg):
    rng = np.random.default_rng(seed)
    if profile == "custom":
        strength = rng.uniform(*strength_range)
        ratio = rng.uniform(*ratio_range)
        low_percentile = rng.uniform(*low_range)
        high_percentile = rng.uniform(*high_range)
        bands = tuple(b.strip().upper() for b in bands_arg.split(",") if b.strip())
    else:
        strength, ratio, low_percentile, high_percentile, bands = choose_profile(profile, rng)

    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycrcb[:, :, 0]
    ll, lh, hl, hh, h, w = haar2d(y)

    if "LH" in bands:
        lh = modify_band(lh, ratio, strength, low_percentile, high_percentile, rng)
    if "HL" in bands:
        hl = modify_band(hl, ratio, strength, low_percentile, high_percentile, rng)
    if "HH" in bands:
        hh = modify_band(hh, ratio, strength, low_percentile, high_percentile, rng)

    y2 = y.copy()
    y2[:h, :w] = ihaar2d(ll, lh, hl, hh, h, w)
    ycrcb[:, :, 0] = np.clip(y2, 0, 255)
    return cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_dwt_haar/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--profile", choices=["ultra", "weak", "balanced", "hard", "mixed", "custom"], default="mixed")
    parser.add_argument("--strength", default=None)
    parser.add_argument("--coeff_ratio", default=None)
    parser.add_argument("--low_percentile", default=None)
    parser.add_argument("--high_percentile", default=None)
    parser.add_argument("--bands", default="LH,HL,HH")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    strength_range = parse_range(args.strength, 0.03, 0.35)
    ratio_range = parse_range(args.coeff_ratio, 0.0002, 0.006)
    low_range = parse_range(args.low_percentile, 70.0, 92.0)
    high_range = parse_range(args.high_percentile, 90.0, 99.5)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")

    images = list_images(input_dir)
    if not images:
        raise RuntimeError(f"no images found: {input_dir}")

    ok = 0
    skipped = 0
    for idx, path in enumerate(images):
        try:
            rgb = load_rgb(path, args.size)
            stego = embed_dwt_haar(
                rgb=rgb,
                profile=args.profile,
                strength_range=strength_range,
                ratio_range=ratio_range,
                low_range=low_range,
                high_range=high_range,
                seed=args.seed + idx,
                bands_arg=args.bands,
            )
            save_rgb(stego, output_dir / f"{path.stem}.png")
            ok += 1
        except Exception as exc:
            skipped += 1
            print(f"[SKIP] {path.name}: {exc}")

    print(f"done: {ok} DWT Haar stego images saved to {output_dir} / skipped: {skipped} / profile: {args.profile}")


if __name__ == "__main__":
    main()
