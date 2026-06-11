import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".pgm"}
SCRIPT_BY_VARIANT = {
    "dct_mid": "build_dct_mid_stego.py",
    "dwt_haar": "build_dwt_haar_stego.py",
    "aes_random_lsb": "build_aes_random_lsb_stego.py",
    "channel_lsb": "build_channel_lsb_stego.py",
    "alpha_lsb": "build_alpha_lsb_stego.py",
    "edge_adaptive_lsb": "build_edge_adaptive_lsb_stego.py",
    "texture_adaptive_lsb": "build_texture_adaptive_lsb_stego.py",
    "watermark": "build_watermark_stego.py",
}


def count_images(path):
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.suffix.lower() in EXTS)


def copy_tree(src, dst):
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            copy_tree(item, target)
        elif item.suffix.lower() in EXTS:
            shutil.copy2(item, target)


def run_builder(script, input_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(script),
        "--input_dir",
        str(input_dir),
        "--output_dir",
        str(output_dir),
        "--size",
        "256",
    ]
    print(" ".join(f'"{x}"' if " " in x else x for x in cmd))
    subprocess.check_call(cmd)


def infer_variant_from_script(script):
    if not script:
        return ""
    name = Path(script).name
    for variant, script_name in SCRIPT_BY_VARIANT.items():
        if name == script_name:
            return variant
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--variant", default="")
    parser.add_argument("--script", default="")
    parser.add_argument("--yes", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    root = workspace.parent

    env_variant = os.environ.get("STEGANO_VARIANT", "").strip()
    env_script = os.environ.get("STEGANO_SCRIPT", "").strip()

    variant = (args.variant or env_variant or "").strip()
    script_value = (args.script or env_script or "").strip()

    if not variant:
        variant = infer_variant_from_script(script_value)

    if variant not in SCRIPT_BY_VARIANT:
        valid = ", ".join(sorted(SCRIPT_BY_VARIANT))
        raise SystemExit(f"missing or invalid variant: {variant or '(empty)'}\nvalid variants: {valid}")

    if script_value:
        script = Path(script_value).resolve()
    else:
        script = root / "scripts" / SCRIPT_BY_VARIANT[variant]

    src = workspace / "dataset"
    dst = workspace / f"dataset_{variant}"

    print(f"workspace={workspace}")
    print(f"variant={variant}")
    print(f"script={script}")
    print(f"source_dataset={src}")
    print(f"target_dataset={dst}")

    for required in [src / "train" / "cover", src / "val" / "cover"]:
        if not required.exists():
            raise SystemExit(f"missing source folder: {required}")
        if count_images(required) == 0:
            raise SystemExit(f"no cover images in: {required}")
    if not script.exists():
        raise SystemExit(f"missing builder script: {script}")

    if dst.exists() and str(args.yes).lower() not in {"/yes", "yes", "y"}:
        answer = input(f"{dst} exists. Rebuild stego folders only? Y/N: ").strip().lower()
        if answer != "y":
            print("cancelled")
            return

    for split in ["train", "val"]:
        src_cover = src / split / "cover"
        dst_cover = dst / split / "cover"
        dst_stego = dst / split / "stego"
        if not dst_cover.exists() or count_images(dst_cover) == 0:
            print(f"copy cover: {src_cover} -> {dst_cover}")
            copy_tree(src_cover, dst_cover)
        else:
            print(f"cover already exists: {dst_cover} ({count_images(dst_cover)} images)")
        if dst_stego.exists():
            shutil.rmtree(dst_stego)
        print(f"build stego: {variant} {split}")
        run_builder(script, dst_cover, dst_stego)

    print(f"done: {dst}")


if __name__ == "__main__":
    main()
