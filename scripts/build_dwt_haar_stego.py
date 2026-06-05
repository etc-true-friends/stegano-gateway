import argparse
from pathlib import Path
import numpy as np
import cv2
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
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(path)


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


def embed_dwt_haar(rgb, strength, seed, bands):
    rng = np.random.default_rng(seed)
    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycrcb[:, :, 0]
    ll, lh, hl, hh, h, w = haar2d(y)

    if "LH" in bands:
        lh += rng.choice([-strength, strength], size=lh.shape)
    if "HL" in bands:
        hl += rng.choice([-strength, strength], size=hl.shape)
    if "HH" in bands:
        hh += rng.choice([-strength, strength], size=hh.shape)

    y2 = y.copy()
    y2[:h, :w] = ihaar2d(ll, lh, hl, hh, h, w)
    ycrcb[:, :, 0] = np.clip(y2, 0, 255)
    return cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_dwt_haar/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--strength", type=float, default=3.0)
    parser.add_argument("--bands", default="LH,HL")
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

    bands = {x.strip().upper() for x in args.bands.split(",") if x.strip()}

    for idx, path in enumerate(images):
        rgb = load_rgb(path, args.size)
        stego = embed_dwt_haar(rgb, args.strength, args.seed + idx, bands)
        save_rgb(stego, output_dir / f"{path.stem}.png")

    print(f"done: {len(images)} DWT Haar stego images saved to {output_dir}")


if __name__ == "__main__":
    main()
