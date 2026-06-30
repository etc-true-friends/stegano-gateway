import argparse
import csv
from pathlib import Path

import torch

from ensemble_predict import load_models, load_weights, predict_image

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".pgm"}


def list_images(path):
    p = Path(path)
    if not p.exists():
        return []
    return sorted(x for x in p.iterdir() if x.suffix.lower() in EXTS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover_dir", required=True)
    parser.add_argument("--stego_dir", required=True)
    parser.add_argument("--models_dir", default="./checkpoints")
    parser.add_argument("--weights_json", default=None)
    parser.add_argument("--output_csv", default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--input_mode", choices=["auto", "rgb", "lsb"], default="auto")
    args = parser.parse_args()

    cover_images = list_images(args.cover_dir)
    stego_images = list_images(args.stego_dir)
    if args.limit > 0:
        cover_images = cover_images[:args.limit]
        stego_images = stego_images[:args.limit]
    if not cover_images or not stego_images:
        raise SystemExit("cover or stego images not found")

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    override_mode = None if args.input_mode == "auto" else args.input_mode
    models = load_models(args.models_dir, device, override_mode)
    weights = load_weights(args.weights_json)

    rows = []
    correct = 0
    total = 0
    method_hits = {}

    targets = [(p, 0) for p in cover_images] + [(p, 1) for p in stego_images]
    for idx, (path, label) in enumerate(targets, start=1):
        result = predict_image(models, path, device, weights)
        pred = 1 if result["result"] == "stego" else 0
        ok = int(pred == label)
        correct += ok
        total += 1
        method_hits[result["estimated_method"]] = method_hits.get(result["estimated_method"], 0) + 1
        rows.append({
            "image": str(path),
            "label": "stego" if label else "cover",
            "prediction": result["result"],
            "correct": ok,
            "final_cover_prob": result["final_cover_prob"],
            "final_stego_prob": result["final_stego_prob"],
            "estimated_method": result["estimated_method"],
            "estimated_method_stego_prob": result["estimated_method_stego_prob"],
        })
        if idx % 50 == 0 or idx == len(targets):
            print(f"processed={idx}/{len(targets)} accuracy={correct / total * 100:.2f}%")

    accuracy = correct / total * 100.0
    print(f"final_accuracy={accuracy:.2f}%")
    print("estimated_method_count:")
    for key, value in sorted(method_hits.items(), key=lambda x: x[1], reverse=True):
        print(f"  {key}: {value}")

    if args.output_csv and rows:
        out = Path(args.output_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"csv={out}")


if __name__ == "__main__":
    main()
