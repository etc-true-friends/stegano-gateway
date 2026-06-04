"""This module is use to train the Srnet model."""

import logging
import os
import sys
import time

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms

from PIL import PngImagePlugin, ImageFile
PngImagePlugin.MAX_TEXT_CHUNK = 100 * 1024 * 1024
ImageFile.LOAD_TRUNCATED_IMAGES = True  # 깨진 이미지 들어와도 팅기지 말고 강제 로드!

from dataset import dataset
from opts.options import arguments
from model.model import Srnet
from utils.utils import (
    latest_checkpoint,
    saver,
    weights_init,
)

opt = arguments()

logging.basicConfig(
    filename="training.log",
    format="%(asctime)s %(message)s",
    level=logging.DEBUG,
)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

if __name__ == "__main__":

    train_data = dataset.DatasetLoad(
        cover_path=opt.cover_path,
        stego_path=opt.stego_path,
        size=opt.train_size,
        transform=transforms.Compose([
            transforms.ToTensor(),
        ]),
    )

    val_data = dataset.DatasetLoad(
        cover_path=opt.valid_cover_path,
        stego_path=opt.valid_stego_path,
        size=opt.val_size,
        transform=transforms.ToTensor(),
    )

    if len(train_data) == 0:
        print("[-] 학습 가능한 train cover/stego 쌍이 없습니다. 파일명과 경로를 확인하세요.")
        sys.exit(1)

    if len(val_data) == 0:
        print("[-] 학습 가능한 validation cover/stego 쌍이 없습니다. 파일명과 경로를 확인하세요.")
        sys.exit(1)

    print(f"[+] Train pairs: {len(train_data)}, Validation pairs: {len(val_data)}")

    # Creating training and validation loader.
    train_loader = DataLoader(
        train_data, 
        batch_size=opt.batch_size, 
        shuffle=True,
        num_workers=0,       # 윈도우 프로세스 꼬임 방지
        pin_memory=False     # dataset.py 충돌 방지
    )
    valid_loader = DataLoader(
        val_data, 
        batch_size=opt.batch_size, 
        shuffle=False,
        num_workers=0,
        pin_memory=False
    )

    # model creation and initialization.
    model = Srnet()
    model.to(device)
    model = model.apply(weights_init)

    # Loss function and Optimizer
    loss_fn = nn.NLLLoss()
    
    # [과적합 방어막 1] Adamax + weight_decay(L2 정규화) 2e-4 주입
    optimizer = torch.optim.Adamax(
        model.parameters(),
        lr=opt.lr,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=2e-4, 
    )

    # [과적합 방어막 2] LR 스케줄러: 지정된 에폭(예: 전체의 70%, 90% 지점)에서만 1/10 감소
    scheduler = torch.optim.lr_scheduler.MultiStepLR(
        optimizer, 
        milestones=[int(opt.num_epochs * 0.7), int(opt.num_epochs * 0.9)], 
        gamma=0.1
    )

    os.makedirs(opt.checkpoints_dir, exist_ok=True)

    check_point = latest_checkpoint(opt.checkpoints_dir)
    best_model_path = os.path.join(opt.checkpoints_dir, "best_srnet_model.pt")
    best_valid_loss = float("inf")

    if not check_point:
        START_EPOCH = 1
        print("No checkpoints found!!, Training started... ")
    else:
        pth = os.path.join(opt.checkpoints_dir, f"net_{check_point}.pt")
        ckpt = torch.load(pth, map_location=device, weights_only=False)
        START_EPOCH = ckpt["epoch"] + 1
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        if "scheduler_state_dict" in ckpt:
            scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        best_valid_loss = ckpt.get("best_valid_loss", ckpt.get("valid_loss", float("inf")))
        print(f"Model loaded from epoch {ckpt['epoch']}. Next epoch: {START_EPOCH}")

    if START_EPOCH > opt.num_epochs:
        print(f"Already trained through epoch {START_EPOCH - 1}. Increase --num_epochs to continue training.")
        sys.exit(0)

    if os.path.exists(best_model_path):
        best_ckpt = torch.load(best_model_path, map_location=device, weights_only=False)
        best_valid_loss = min(best_valid_loss, best_ckpt.get("best_valid_loss", best_ckpt.get("valid_loss", float("inf"))))

    for epoch in range(START_EPOCH, opt.num_epochs + 1):
        training_loss = []
        training_accuracy = []
        validation_loss = []
        validation_accuracy = []

        # Training
        model.train()
        st_time = time.time()

        for i, train_batch in enumerate(train_loader):
            images = torch.cat((train_batch["cover"], train_batch["stego"]), 0)
            labels = torch.cat(
                (train_batch["label"][0], train_batch["label"][1]), 0
            )
            images = images.to(device, dtype=torch.float)
            labels = labels.to(device, dtype=torch.long)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = loss_fn(outputs, labels)
            loss.backward()
            optimizer.step()
            
            training_loss.append(loss.item())
            prediction = outputs.data.max(1)[1]
            accuracy = (
                prediction.eq(labels.data).sum() * 100.0 / (labels.size()[0])
            )
            training_accuracy.append(accuracy.item())

            sys.stdout.write(
                f"\r Epoch:{epoch}/{opt.num_epochs}"
                f" Batch:{i+1}/{len(train_loader)}"
                f" Loss:{training_loss[-1]:.4f}"
                f" Acc:{training_accuracy[-1]:.2f}"
                f" LR:{optimizer.param_groups[0]['lr']:.6f}"
            )

        # Validation
        model.eval()
        with torch.no_grad():
            for i, val_batch in enumerate(valid_loader):
                images = torch.cat((val_batch["cover"], val_batch["stego"]), 0)
                labels = torch.cat(
                    (val_batch["label"][0], val_batch["label"][1]), 0
                )
                images = images.to(device, dtype=torch.float)
                labels = labels.to(device, dtype=torch.long)

                outputs = model(images)
                loss = loss_fn(outputs, labels)
                validation_loss.append(loss.item())
                
                prediction = outputs.data.max(1)[1]
                accuracy = (
                    prediction.eq(labels.data).sum()
                    * 100.0
                    / (labels.size()[0])
                )
                validation_accuracy.append(accuracy.item())

        avg_train_loss = sum(training_loss) / len(training_loss)
        avg_valid_loss = sum(validation_loss) / len(validation_loss)
        avg_train_acc = sum(training_accuracy) / len(training_accuracy)
        avg_valid_acc = sum(validation_accuracy) / len(validation_accuracy)

        message = (
            f"Epoch: {epoch}. "
            f"Train Loss:{avg_train_loss:.5f}. "
            f"Valid Loss:{avg_valid_loss:.5f}. "
            f"Train Acc:{avg_train_acc:.2f} "
            f"Valid Acc:{avg_valid_acc:.2f} "
        )
        print("\n", message)
        logging.info(message)

        # 에폭 종료 후 스케줄러를 먼저 갱신한 뒤 체크포인트에 저장
        scheduler.step()

        state = {
            "epoch": epoch,
            "opt": opt,
            "train_loss": avg_train_loss,
            "valid_loss": avg_valid_loss,
            "train_accuracy": avg_train_acc,
            "valid_accuracy": avg_valid_acc,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "best_valid_loss": min(best_valid_loss, avg_valid_loss),
            "lr": optimizer.param_groups[0]["lr"],
        }

        saver(state, opt.checkpoints_dir, epoch)
        print(f" Checkpoint saved -> {os.path.join(opt.checkpoints_dir, f'net_{epoch}.pt')}")

        if avg_valid_loss < best_valid_loss:
            best_valid_loss = avg_valid_loss
            state["best_valid_loss"] = best_valid_loss
            torch.save(state, best_model_path)
            print(f" [BEST] Valid Loss 갱신! 베스트 모델 저장 완료 -> {best_model_path}")
            logging.info("Best model saved.")

