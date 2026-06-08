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

    ll = (a + b + c + d) / 4.0
    lh = (a - b + c - d) / 4.0
    hl = (a + b - c - d) / 4.0
    hh = (a - b - c + d) / 4.0
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


def band_candidates(band, percentile):
    mag = np.abs(band)
    if mag.size == 0:
        return np.array([], dtype=np.int64)
    threshold = np.percentile(mag, percentile)
    idx = np.flatnonzero(mag >= threshold)
    if idx.size == 0:
        idx = np.arange(band.size)
    return idx


def choose_profile(profile, rng):
    if profile == "weak":
        bands = [("LH",), ("HL",), ("HH",), ("LH", "HL")][rng.integers(0, 4)]
        return rng.uniform(0.12, 0.55), rng.uniform(0.002, 0.012), rng.uniform(65.0, 90.0), bands
    if profile == "balanced":
        bands = [("LH",), ("HL",), ("HH",), ("LH", "HL"), ("HL", "HH")][rng.integers(0, 5)]
        return rng.uniform(0.25, 1.25), rng.uniform(0.004, 0.035), rng.uniform(55.0, 85.0), bands
    if profile == "hard":
        bands = [("LH", "HL"), ("LH", "HH"), ("HL", "HH"), ("LH", "HL", "HH")][rng.integers(0, 4)]
        return rng.uniform(1.0, 2.5), rng.uniform(0.02, 0.08), rng.uniform(45.0, 75.0), bands
    if profile == "mixed":
        r = rng.random()
        if r < 0.60:
            return choose_profile("weak", rng)
        if r < 0.90:
            return choose_profile("balanced", rng)
        return choose_profile("hard", rng)
    raise ValueError(f"unknown profile: {profile}")


def modify_band(band, ratio, strength, percentile, rng):
    flat = band.reshape(-1)
    candidates = band_candidates(band, percentile)
    count = max(1, int(flat.size * ratio))
    count = min(count, candidates.size)
    selected = rng.choice(candidates, size=count, replace=False)

    signs = rng.choice([-1.0, 1.0], size=count).astype(np.float32)
    jitter = rng.uniform(0.65, 1.35, size=count).astype(np.float32)
    flat[selected] = flat[selected] + signs * strength * jitter
    return band


def embed_dwt_haar(rgb, profile, strength_range, ratio_range, percentile_range, seed, bands_arg):
    rng = np.random.default_rng(seed)

    if profile == "custom":
        strength = rng.uniform(*strength_range)
        ratio = rng.uniform(*ratio_range)
        percentile = rng.uniform(*percentile_range)
        bands = tuple(b.strip().upper() for b in bands_arg.split(",") if b.strip())
    else:
        strength, ratio, percentile, bands = choose_profile(profile, rng)

    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycrcb[:, :, 0]

    ll, lh, hl, hh, h, w = haar2d(y)

    if "LH" in bands:
        lh = modify_band(lh, ratio, strength, percentile, rng)
    if "HL" in bands:
        hl = modify_band(hl, ratio, strength, percentile, rng)
    if "HH" in bands:
        hh = modify_band(hh, ratio, strength, percentile, rng)

    y2 = y.copy()
    y2[:h, :w] = ihaar2d(ll, lh, hl, hh, h, w)
    ycrcb[:, :, 0] = np.clip(y2, 0, 255)
    return cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_dwt_haar/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--profile", choices=["weak", "balanced", "hard", "mixed", "custom"], default="mixed")
    parser.add_argument("--strength", default=None)
    parser.add_argument("--coeff_ratio", default=None)
    parser.add_argument("--percentile", default=None)
    parser.add_argument("--bands", default="LH,HL,HH")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    strength_range = parse_range(args.strength, 0.12, 1.25)
    ratio_range = parse_range(args.coeff_ratio, 0.002, 0.035)
    percentile_range = parse_range(args.percentile, 55.0, 90.0)

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
                percentile_range=percentile_range,
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
