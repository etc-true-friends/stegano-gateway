import argparse
from pathlib import Path
from PIL import Image


def list_images(path):
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    return sorted([p for p in Path(path).iterdir() if p.suffix.lower() in exts])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_cover")
    parser.add_argument("--size", type=int, default=256)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")

    images = list_images(input_dir)
    if not images:
        raise RuntimeError(f"no images found: {input_dir}")

    for path in images:
        img = Image.open(path).convert("RGB")
        if args.size > 0:
            img = img.resize((args.size, args.size), Image.Resampling.LANCZOS)
        img.save(output_dir / f"{path.stem}.png")

    print(f"done: {len(images)} cover images saved to {output_dir}")


if __name__ == "__main__":
    main()
