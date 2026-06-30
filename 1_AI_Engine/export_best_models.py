import argparse
import shutil
from pathlib import Path

METHODS = {
    "original": "checkpoints",
    "dct_mid": "checkpoints_dct_mid",
    "dwt_haar": "checkpoints_dwt_haar",
    "aes_random_lsb": "checkpoints_aes_random_lsb",
    "channel_lsb": "checkpoints_channel_lsb",
    "alpha_lsb": "checkpoints_alpha_lsb",
    "edge_adaptive_lsb": "checkpoints_edge_adaptive_lsb",
    "texture_adaptive_lsb": "checkpoints_texture_adaptive_lsb",
    "watermark": "checkpoints_watermark",
}

EXPORT_NAMES = {
    "original": "lsb_model.pt",
    "dct_mid": "dct_model.pt",
    "dwt_haar": "dwt_model.pt",
    "aes_random_lsb": "aes_lsb_model.pt",
    "channel_lsb": "channel_lsb_model.pt",
    "alpha_lsb": "alpha_lsb_model.pt",
    "edge_adaptive_lsb": "edge_adaptive_lsb.pt",
    "texture_adaptive_lsb": "texture_adaptive_lsb_model.pt",
    "watermark": "watermark_model.pt",
}


def project_root():
    return Path(__file__).resolve().parents[1]


def export_one(method):
    root = project_root()
    workspace = root / "4_Local_Workspace"
    checkpoint_dir = workspace / METHODS[method]
    # Edge LSB uses balanced best if available because valid acc can improve
    # while valid loss fluctuates. Other models keep the old best_srnet_model rule.
    candidates = []
    if method == "edge_adaptive_lsb":
        candidates.extend([
            checkpoint_dir / "best_acc_model.pt",
            checkpoint_dir / "best_balanced_model.pt",
            checkpoint_dir / "best_srnet_model.pt",
            checkpoint_dir / "best_loss_model.pt",
        ])
    else:
        candidates.extend([
            checkpoint_dir / "best_srnet_model.pt",
            checkpoint_dir / "best_loss_model.pt",
            checkpoint_dir / "best_srnet_finetuned.pt",
        ])

    src = next((p for p in candidates if p.exists()), candidates[0])
    if not src.exists():
        print(f"SKIP {method}: missing best model in {checkpoint_dir}")
        return False

    models = root / "1_AI_Engine" / "checkpoints"
    models.mkdir(parents=True, exist_ok=True)
    dst = models / EXPORT_NAMES.get(method, f"{method}.pt")
    shutil.copy2(src, dst)
    print(f"EXPORTED {method}: {src.name} -> {dst}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=METHODS.keys())
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    if args.all:
        ok = 0
        for method in METHODS:
            ok += int(export_one(method))
        print(f"exported={ok}/{len(METHODS)}")
        return

    method = args.method
    if args.interactive or not method:
        for idx, key in enumerate(METHODS, start=1):
            print(f"{idx}. {key}")
        selected = input("Select method: ").strip()
        keys = list(METHODS.keys())
        if not selected.isdigit() or not 1 <= int(selected) <= len(keys):
            raise SystemExit("invalid selection")
        method = keys[int(selected) - 1]
    export_one(method)


if __name__ == "__main__":
    main()
