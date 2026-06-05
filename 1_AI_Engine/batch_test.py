import argparse
import os
from glob import glob

import numpy as np
import torch
from PIL import Image

from model.model import Srnet


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover_glob", default="../4_Local_Workspace/dataset_finetune/train/cover/*.png")
    parser.add_argument("--stego_glob", default="../4_Local_Workspace/dataset_finetune/train/stego/*.png")
    parser.add_argument("--checkpoint_path", default="../4_Local_Workspace/checkpoints/best_srnet_finetuned.pt")
    parser.add_argument("--batch_size", type=int, default=40)
    return parser.parse_args()


def load_state_dict(checkpoint_path, device):
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        return checkpoint["model_state_dict"]
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        return checkpoint["state_dict"]
    return checkpoint


def main():
    opt = parse_args()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[*] 대량 배치 테스트 구동 장치: {device}")

    cover_image_names = sorted(glob(opt.cover_glob))
    stego_image_names = sorted(glob(opt.stego_glob))

    if not cover_image_names or not stego_image_names:
        print("[-] 테스트할 이미지를 찾을 수 없습니다. 경로를 확인해주세요.")
        return

    if opt.batch_size % 2 != 0:
        print("[-] batch_size는 짝수여야 합니다.")
        return

    print(f"[*] Cover {len(cover_image_names)}장, Stego {len(stego_image_names)}장 로드 완료.")

    model = Srnet().to(device)
    model.load_state_dict(load_state_dict(opt.checkpoint_path, device), strict=True)
    model.eval()
    print("[+] 파인튜닝 통합 가중치 로드 완료.\n")

    test_accuracy = []
    half_batch = opt.batch_size // 2

    with torch.no_grad():
        for idx in range(0, min(len(cover_image_names), len(stego_image_names)), half_batch):
            cover_batch = cover_image_names[idx:idx + half_batch]
            stego_batch = stego_image_names[idx:idx + half_batch]

            if len(cover_batch) < half_batch or len(stego_batch) < half_batch:
                break

            batch = []
            batch_labels = []
            for stego_path, cover_path in zip(stego_batch, cover_batch):
                batch.append(stego_path)
                batch_labels.append(1)
                batch.append(cover_path)
                batch_labels.append(0)

            images = torch.empty((len(batch), 3, 256, 256), dtype=torch.float)

            for i, image_path in enumerate(batch):
                with Image.open(image_path) as pil_img:
                    pil_img = pil_img.convert("RGB")
                    if pil_img.size != (256, 256):
                        pil_img = pil_img.resize((256, 256), Image.Resampling.BILINEAR)
                    img_array = np.array(pil_img)

                images[i] = torch.from_numpy(img_array).permute(2, 0, 1).float() / 255.0

            image_tensor = images.to(device)
            batch_labels_tensor = torch.tensor(batch_labels, dtype=torch.long).to(device)

            outputs = model(image_tensor)
            prediction = outputs.data.max(1)[1]

            accuracy = prediction.eq(batch_labels_tensor.data).sum() * 100.0 / batch_labels_tensor.size(0)
            test_accuracy.append(accuracy.item())

            print(f"    - 현재 배치 정확도 측정 중... [ {accuracy.item():.2f}% ]")

    if test_accuracy:
        final_acc = sum(test_accuracy) / len(test_accuracy)
        print(f"\n[+] 최종 대량 블라인드 테스트 평균 정확도 (Test Accuracy) = {final_acc:.2f}%")


if __name__ == "__main__":
    main()
