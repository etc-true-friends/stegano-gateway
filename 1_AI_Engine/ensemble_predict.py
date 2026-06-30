import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageFile, PngImagePlugin

from model.model import Srnet

ImageFile.LOAD_TRUNCATED_IMAGES = True
PngImagePlugin.MAX_TEXT_CHUNK = 1024 * 1024 * 1024
PngImagePlugin.MAX_TEXT_MEMORY = 1024 * 1024 * 1024


def is_lfs_pointer(path):
    try:
        with open(path, "rb") as f:
            head = f.read(80)
        return head.startswith(b"version https://git-lfs.github.com/spec")
    except OSError:
        return False


def infer_input_mode(checkpoint, model_name, explicit_mode=None):
    if explicit_mode in {"rgb", "lsb"}:
        return explicit_mode
    if isinstance(checkpoint, dict):
        opt = checkpoint.get("opt")
        mode = getattr(opt, "input_mode", None)
        if isinstance(mode, str) and mode.strip():
            return mode.strip().lower()
    name = str(model_name).lower()
    return "lsb" if ("edge_adaptive_lsb" in name or "edge" in name) else "rgb"


def load_checkpoint(path, device):
    if is_lfs_pointer(path):
        raise RuntimeError("Git LFS pointer file. Run git lfs pull or replace it with the real .pt model file.")
    return torch.load(path, map_location=device, weights_only=False)


def extract_state_dict(checkpoint):
    if isinstance(checkpoint, dict):
        if "model_state_dict" in checkpoint:
            return checkpoint["model_state_dict"]
        if "state_dict" in checkpoint:
            return checkpoint["state_dict"]
    return checkpoint


def load_models(models_dir, device, input_mode_override=None):
    paths = sorted(Path(models_dir).glob("*.pt"))
    if not paths:
        raise FileNotFoundError(f"no .pt models found: {models_dir}")
    models = []
    skipped = []
    for path in paths:
        try:
            checkpoint = load_checkpoint(path, device)
            model = Srnet().to(device)
            model.load_state_dict(extract_state_dict(checkpoint), strict=True)
            model.eval()
            models.append({
                "name": path.stem,
                "model": model,
                "input_mode": infer_input_mode(checkpoint, path.stem, input_mode_override),
            })
        except Exception as exc:
            skipped.append((path.name, str(exc)))
    for name, reason in skipped:
        print(f"SKIP_MODEL {name}: {reason}")
    if not models:
        raise RuntimeError("no loadable models found. Check 1_AI_Engine/checkpoints and Git LFS model files.")
    return models


def image_to_tensor(image_path, device, input_mode="rgb"):
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        if img.size != (256, 256):
            resample = Image.Resampling.NEAREST if input_mode == "lsb" else Image.Resampling.BILINEAR
            img = img.resize((256, 256), resample)
        arr = np.array(img)

    if input_mode == "lsb":
        tensor = torch.from_numpy((arr.astype(np.uint8) & 1).astype(np.float32)).permute(2, 0, 1)
    else:
        tensor = torch.from_numpy(arr).permute(2, 0, 1).float() / 255.0
    return tensor.unsqueeze(0).to(device)


def predict_image(models, image_path, device, weights=None):
    cached_tensors = {}
    rows = []
    stego_values = []
    weight_values = []

    with torch.no_grad():
        for entry in models:
            name = entry["name"]
            model = entry["model"]
            input_mode = entry["input_mode"]

            if input_mode not in cached_tensors:
                cached_tensors[input_mode] = image_to_tensor(image_path, device, input_mode)
            tensor = cached_tensors[input_mode]

            output = model(tensor)
            prob = torch.exp(output).squeeze(0).detach().cpu().numpy()
            weight = float(weights.get(name, 1.0)) if weights else 1.0
            rows.append({
                "model": name,
                "cover_prob": float(prob[0]),
                "stego_prob": float(prob[1]),
                "weight": weight,
                "input_mode": input_mode,
            })
            stego_values.append(float(prob[1]) * weight)
            weight_values.append(weight)

    final_stego = sum(stego_values) / max(sum(weight_values), 1e-12)
    final_cover = 1.0 - final_stego
    best = max(rows, key=lambda x: x["stego_prob"])
    result = "stego" if final_stego >= 0.5 else "cover"
    return {
        "result": result,
        "final_cover_prob": final_cover,
        "final_stego_prob": final_stego,
        "estimated_method": best["model"],
        "estimated_method_stego_prob": best["stego_prob"],
        "models": rows,
    }


def load_weights(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {str(k): float(v) for k, v in data.items()}


def print_result(image, result):
    print(f"image={image}")
    print(f"final_result={result['result']}")
    print(f"final_cover_prob={result['final_cover_prob']:.6f}")
    print(f"final_stego_prob={result['final_stego_prob']:.6f}")
    print(f"estimated_method={result['estimated_method']}")
    print("model_details:")
    for row in sorted(result["models"], key=lambda x: x["stego_prob"], reverse=True):
        print(
            f"  {row['model']}: cover={row['cover_prob']:.6f}, "
            f"stego={row['stego_prob']:.6f}, weight={row['weight']:.3f}, input_mode={row['input_mode']}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--models_dir", default="./checkpoints")
    parser.add_argument("--weights_json", default=None)
    parser.add_argument("--output_csv", default=None)
    parser.add_argument("--input_mode", choices=["auto", "rgb", "lsb"], default="auto")
    args = parser.parse_args()

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    override_mode = None if args.input_mode == "auto" else args.input_mode
    models = load_models(args.models_dir, device, override_mode)
    weights = load_weights(args.weights_json)
    result = predict_image(models, args.image, device, weights)
    print_result(args.image, result)

    if args.output_csv:
        out = Path(args.output_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["image", "model", "cover_prob", "stego_prob", "weight", "input_mode"])
            writer.writeheader()
            for row in result["models"]:
                writer.writerow({"image": args.image, **row})
        print(f"csv={out}")


if __name__ == "__main__":
    main()
