import argparse
import random
import shutil
from pathlib import Path
from PIL import Image

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".pgm"}


def list_images(path):
    if not path.exists():
        return []
    return sorted([p for p in path.rglob("*") if p.suffix.lower() in EXTS])


def save_cover(src, dst, size):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img = img.convert("RGB")
        w, h = img.size
        m = min(w, h)
        left = (w - m) // 2
        top = (h - m) // 2
        img = img.crop((left, top, left + m, top + m))
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        img.save(dst, format="PNG")


def clear_dir(path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", default="")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--train_ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--yes", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    root = workspace.parent
    input_dir = Path(args.input).resolve() if args.input else workspace / "real_images"
    dataset = workspace / "dataset"

    images = list_images(input_dir)
    if not images:
        raise SystemExit(f"no source images found: {input_dir}\nPut images in 4_Local_Workspace\\real_images first.")

    train_cover = dataset / "train" / "cover"
    val_cover = dataset / "val" / "cover"
    train_stego = dataset / "train" / "stego"
    val_stego = dataset / "val" / "stego"

    existing = list_images(train_cover) + list_images(val_cover)
    if existing and str(args.yes).lower() not in {"yes", "y", "/yes"}:
        answer = input(f"{dataset} already has cover images. Rebuild cover dataset? Y/N: ").strip().lower()
        if answer != "y":
            print("cancelled")
            return

    clear_dir(train_cover)
    clear_dir(val_cover)
    if train_stego.exists():
        shutil.rmtree(train_stego)
    if val_stego.exists():
        shutil.rmtree(val_stego)

    random.seed(args.seed)
    random.shuffle(images)
    n_train = int(len(images) * args.train_ratio)
    train_files = images[:n_train]
    val_files = images[n_train:]

    for i, src in enumerate(train_files):
        save_cover(src, train_cover / f"train_{i:06d}.png", args.size)
    for i, src in enumerate(val_files):
        save_cover(src, val_cover / f"val_{i:06d}.png", args.size)

    print(f"source images: {len(images)}")
    print(f"train cover: {len(train_files)} -> {train_cover}")
    print(f"val cover: {len(val_files)} -> {val_cover}")
    print("next: build variant dataset from workspace menu")


if __name__ == "__main__":
    main()
