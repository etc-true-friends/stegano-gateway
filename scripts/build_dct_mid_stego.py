import argparse
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

MID_FREQ = [(2, 3), (3, 2), (2, 4), (4, 2), (3, 3), (1, 4), (4, 1)]


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


def embed_dct_mid(rgb, strength, seed):
    rng = np.random.default_rng(seed)
    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycrcb[:, :, 0]
    h, w = y.shape
    h8 = h - (h % 8)
    w8 = w - (w % 8)
    out = y.copy()

    for yy in range(0, h8, 8):
        for xx in range(0, w8, 8):
            block = y[yy:yy + 8, xx:xx + 8] - 128.0
            dct = cv2.dct(block)
            u, v = MID_FREQ[rng.integers(0, len(MID_FREQ))]
            bit = rng.integers(0, 2)
            sign = 1.0 if bit == 1 else -1.0
            dct[u, v] = sign * (abs(dct[u, v]) + strength)
            idct = cv2.idct(dct) + 128.0
            out[yy:yy + 8, xx:xx + 8] = idct

    ycrcb[:, :, 0] = np.clip(out, 0, 255)
    return cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_dct_mid/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--strength", type=float, default=8.0)
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
        stego = embed_dct_mid(rgb, args.strength, args.seed + idx)
        save_rgb(stego, output_dir / f"{path.stem}.png")

    print(f"done: {len(images)} DCT mid-frequency stego images saved to {output_dir}")


if __name__ == "__main__":
    main()
