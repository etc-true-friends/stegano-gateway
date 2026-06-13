import argparse
from pathlib import Path

METHODS = [
    "dct_mid",
    "dwt_haar",
    "aes_random_lsb",
    "channel_lsb",
    "alpha_lsb",
    "edge_adaptive_lsb",
    "texture_adaptive_lsb",
    "watermark",
]


def make(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    workspace = root / "4_Local_Workspace"

    for split in ["train", "val", "test"]:
        make(workspace / "dataset" / split / "cover")
        make(workspace / "dataset" / split / "stego")

    for name in ["real_images", "models", "test_images", "ensemble_reports"]:
        make(workspace / name)

    make(workspace / "checkpoints")
    for method in METHODS:
        make(workspace / f"dataset_{method}" / "train" / "cover")
        make(workspace / f"dataset_{method}" / "train" / "stego")
        make(workspace / f"dataset_{method}" / "val" / "cover")
        make(workspace / f"dataset_{method}" / "val" / "stego")
        make(workspace / f"checkpoints_{method}")

    print(f"workspace ready: {workspace}")


if __name__ == "__main__":
    main()
