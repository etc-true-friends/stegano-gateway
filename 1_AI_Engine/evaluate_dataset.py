"""Evaluate an SRNet checkpoint on a paired cover/stego dataset."""

import argparse
import os

import numpy as np
import torch
from PIL import Image, ImageFile

from model.model import Srnet


ImageFile.LOAD_TRUNCATED_IMAGES = True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--dataset_dir", required=True)
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument("--max_pairs", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=32)
    return parser.parse_args()


def list_pairs(dataset_dir, split, max_pairs):
    cover_dir = os.path.join(dataset_dir, split, "cover")
    stego_dir = os.path.join(dataset_dir, split, "stego")
    valid_exts = (".png", ".jpg", ".jpeg", ".pgm")

    cover_files = {
        name for name in os.listdir(cover_dir)
        if name.lower().endswith(valid_exts)
    }
    stego_files = {
        name for name in os.listdir(stego_dir)
        if name.lower().endswith(valid_exts)
    }
    names = sorted(cover_files.intersection(stego_files))
    if max_pairs is not None:
        names = names[:max_pairs]

    return [(os.path.join(cover_dir, name), os.path.join(stego_dir, name)) for name in names]


def load_image(path):
    with Image.open(path) as img:
        img = img.convert("RGB")
        if img.size != (256, 256):
            img = img.resize((256, 256), Image.Resampling.BILINEAR)
        arr = np.asarray(img, dtype=np.float32) / 255.0
        return torch.from_numpy(arr).permute(2, 0, 1)


def load_model(model_path, device):
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    state_dict = checkpoint.get("model_state_dict", checkpoint)

    model = Srnet().to(device)
    model.load_state_dict(state_dict)
    model.eval()
    return model


def main():
    args = parse_args()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = load_model(args.model_path, device)
    pairs = list_pairs(args.dataset_dir, args.split, args.max_pairs)

    total = 0
    correct = 0
    cover_total = 0
    cover_false_positive = 0
    stego_total = 0
    stego_detected = 0

    with torch.no_grad():
        for start in range(0, len(pairs), args.batch_size):
            chunk = pairs[start:start + args.batch_size]
            images = []
            labels = []

            for cover_path, stego_path in chunk:
                images.append(load_image(cover_path))
                labels.append(0)
                images.append(load_image(stego_path))
                labels.append(1)

            image_tensor = torch.stack(images).to(device, dtype=torch.float)
            label_tensor = torch.tensor(labels, dtype=torch.long, device=device)

            outputs = model(image_tensor)
            preds = outputs.argmax(dim=1)

            total += label_tensor.numel()
            correct += (preds == label_tensor).sum().item()

            cover_mask = label_tensor == 0
            stego_mask = label_tensor == 1
            cover_total += cover_mask.sum().item()
            stego_total += stego_mask.sum().item()
            cover_false_positive += (preds[cover_mask] == 1).sum().item()
            stego_detected += (preds[stego_mask] == 1).sum().item()

    accuracy = correct * 100.0 / total if total else 0.0
    false_positive_rate = cover_false_positive * 100.0 / cover_total if cover_total else 0.0
    stego_recall = stego_detected * 100.0 / stego_total if stego_total else 0.0

    print(f"Model: {args.model_path}")
    print(f"Dataset: {args.dataset_dir} ({args.split})")
    print(f"Pairs: {len(pairs)}")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Cover false positive rate: {false_positive_rate:.2f}%")
    print(f"Stego detection rate: {stego_recall:.2f}%")


if __name__ == "__main__":
    main()
