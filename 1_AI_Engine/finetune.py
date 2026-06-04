import argparse
import os

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from dataset.dataset import DatasetLoad
from model.model import Srnet


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover_path", default="./dataset_finetune/train/cover")
    parser.add_argument("--stego_path", default="./dataset_finetune/train/stego")
    parser.add_argument("--checkpoint_path", default="../4_Local_Workspace/checkpoints/best_srnet_model.pt")
    parser.add_argument("--save_path", default="../4_Local_Workspace/checkpoints/best_srnet_finetuned.pt")
    parser.add_argument("--size", type=int, default=10000)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=0.0001)
    return parser.parse_args()


def main():
    opt = parse_args()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[*] 파인튜닝 구동 장치: {device}")

    print("[*] 데이터셋 로드 중...")
    train_dataset = DatasetLoad(
        opt.cover_path,
        opt.stego_path,
        size=opt.size,
        transform=None,
    )

    if len(train_dataset) == 0:
        print("[-] 학습 가능한 cover/stego 쌍이 없습니다. 양쪽 폴더의 파일명이 같은지 확인하세요.")
        return

    dataloader = DataLoader(
        train_dataset,
        batch_size=opt.batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=False,
    )
    print(f"[+] 총 {len(train_dataset)} 쌍의 이미지 세트 준비 완료.")

    model = Srnet().to(device)
    if not os.path.exists(opt.checkpoint_path):
        print(f"[-] 가중치 파일을 찾을 수 없습니다: {opt.checkpoint_path}")
        return

    checkpoint = torch.load(opt.checkpoint_path, map_location=device, weights_only=False)
    state_dict = checkpoint["model_state_dict"] if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict, strict=True)
    print("[+] 기존 베스트 가중치 로드 완료.")

    criterion = nn.NLLLoss()
    optimizer = optim.Adamax(model.parameters(), lr=opt.lr, weight_decay=1e-4)

    print(f"\n[*] 파인튜닝을 시작합니다. 목표: {opt.epochs} Epochs")

    for epoch in range(opt.epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for i, data in enumerate(dataloader):
            cover = data["cover"].to(device, dtype=torch.float)
            stego = data["stego"].to(device, dtype=torch.float)

            batch_size = cover.size(0)
            labels_cover = torch.zeros(batch_size, dtype=torch.long, device=device)
            labels_stego = torch.ones(batch_size, dtype=torch.long, device=device)

            inputs = torch.cat([cover, stego], dim=0)
            labels = torch.cat([labels_cover, labels_stego], dim=0)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            predicted = outputs.data.max(1)[1]
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            if (i + 1) % 50 == 0:
                print(f"    - Epoch [{epoch + 1}/{opt.epochs}], Step [{i + 1}/{len(dataloader)}], Loss: {loss.item():.4f}")

        epoch_acc = 100 * correct / total
        print(f"[+] Epoch {epoch + 1} 완료 | 평균 Loss: {running_loss / len(dataloader):.4f} | Accuracy: {epoch_acc:.2f}%\n")

    os.makedirs(os.path.dirname(opt.save_path), exist_ok=True)
    torch.save({"model_state_dict": model.state_dict()}, opt.save_path)
    print(f"[+] 파인튜닝 완료. 저장 위치: {opt.save_path}")


if __name__ == "__main__":
    main()
