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

    # [완벽 수정] 절대 경로 고정 및 불필요한 인자 제거 완료
    train_data = dataset.DatasetLoad(
        cover_path=r"D:\final_project\dataset_real\train\cover",
        stego_path=r"D:\final_project\dataset_real\train\stego",
        size=opt.train_size,
        transform=transforms.Compose([
            transforms.ToTensor(),
        ]),
    )

    val_data = dataset.DatasetLoad(
        cover_path=r"D:\final_project\dataset_real\val\cover",
        stego_path=r"D:\final_project\dataset_real\val\stego",
        size=opt.val_size,
        transform=transforms.ToTensor(),
    )

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

    check_point = latest_checkpoint()
    if not check_point:
        START_EPOCH = 1
        if not os.path.exists(opt.checkpoints_dir):
            os.makedirs(opt.checkpoints_dir)
        print("No checkpoints found!!, Retraining started... ")
    else:
        pth = opt.checkpoints_dir + "net_" + str(check_point) + ".pt"
        ckpt = torch.load(pth, weights_only=False)
        START_EPOCH = ckpt["epoch"] + 1
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        print("Model Loaded from epoch " + str(START_EPOCH) + "..")

    # 베스트 모델 판별을 위한 기준 변수 선언
    best_valid_loss = float('inf')

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

        state = {
            "epoch": epoch,
            "opt": opt,
            "train_loss": avg_train_loss,
            "valid_loss": avg_valid_loss,
            "train_accuracy": avg_train_acc,
            "valid_accuracy": avg_valid_acc,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "lr": optimizer.param_groups[0]["lr"],
        }

        # [과적합 방어막 3] 무지성 저장 금지! Valid Loss 최저치일 때만 'best' 모델 1개 덮어쓰기 저장
        if avg_valid_loss < best_valid_loss:
            best_valid_loss = avg_valid_loss
            best_model_path = os.path.join(opt.checkpoints_dir, "best_srnet_model.pt")
            torch.save(state, best_model_path)
            print(f" [BEST] Valid Loss 갱신! 베스트 모델 저장 완료 -> {best_model_path}")
            logging.info("Best model saved.")

        # 에폭 끝난 후 스케줄러 스텝 진행
        scheduler.step()