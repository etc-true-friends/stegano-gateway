"""This module is use to train the Srnet model with Early Stopping, Plateau Decay, and Safe Shutdown."""

import logging
import csv
import os
import sys
import time
import gc  # 메모리 누수 방지를 위한 가비지 컬렉션

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms

from PIL import PngImagePlugin, ImageFile
# 깨진 이미지로 인한 학습 중단 방지
PngImagePlugin.MAX_TEXT_CHUNK = 100 * 1024 * 1024
ImageFile.LOAD_TRUNCATED_IMAGES = True

from dataset import dataset
from opts.options import arguments
from model.model import Srnet
from utils.utils import (
    latest_checkpoint,
    saver,
    weights_init,
)

opt = arguments()

# -------------------------------------------------------------------
# [경로 이스케이프 버그 방지] 슬래시(/) 기반 절대 경로 사용
# -------------------------------------------------------------------
BASE_DATA_PATH = os.environ.get(
    "SRNET_DATASET_DIR",
    "D:/final_project/4_Local_Workspace/dataset_aes_random_lsb",
).replace("\\", "/")

opt.cover_path = f"{BASE_DATA_PATH}/train/cover"
opt.stego_path = f"{BASE_DATA_PATH}/train/stego"
opt.valid_cover_path = f"{BASE_DATA_PATH}/val/cover"
opt.valid_stego_path = f"{BASE_DATA_PATH}/val/stego"

opt.checkpoints_dir = os.environ.get(
    "SRNET_CHECKPOINTS_DIR",
    "D:/final_project/4_Local_Workspace/checkpoints_aes_random_lsb",
).replace("\\", "/")
# -------------------------------------------------------------------

logging.basicConfig(
    filename="training.log",
    format="%(asctime)s %(message)s",
    level=logging.DEBUG,
)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
if device.type == "cuda":
    torch.backends.cudnn.benchmark = opt.cudnn_benchmark
    try:
        torch.set_float32_matmul_precision("high")
    except Exception:
        pass

if __name__ == "__main__":

    # [안전 장치 1] 실제 파일 개수를 확인해 IndexError를 미리 차단
    actual_train_size = len([f for f in os.listdir(opt.cover_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    actual_val_size = len([f for f in os.listdir(opt.valid_cover_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    if actual_train_size == 0 or actual_val_size == 0:
        print("[-] 학습 가능한 train/val 데이터가 없습니다. 데이터셋 생성을 먼저 진행하세요.")
        sys.exit(1)

    train_size = min(opt.train_size, actual_train_size)
    val_size = min(opt.val_size, actual_val_size)

    train_transform = transforms.Compose([
        transforms.ToTensor(),
    ]) if opt.input_mode == "rgb" else None

    train_data = dataset.DatasetLoad(
        cover_path=opt.cover_path,
        stego_path=opt.stego_path,
        size=train_size,  # 요청한 train_size와 실제 파일 개수 중 작은 값 사용
        transform=train_transform,
        input_mode=opt.input_mode,
    )

    val_transform = transforms.Compose([
        transforms.ToTensor(),
    ]) if opt.input_mode == "rgb" else None

    val_data = dataset.DatasetLoad(
        cover_path=opt.valid_cover_path,
        stego_path=opt.valid_stego_path,
        size=val_size,    # 요청한 val_size와 실제 파일 개수 중 작은 값 사용
        transform=val_transform,
        input_mode=opt.input_mode,
    )

    print(f"[+] 데이터 감지 완료 -> Train pairs: {len(train_data)}, Validation pairs: {len(val_data)}")

    # Data Loaders
    loader_kwargs = {
        "num_workers": opt.num_workers,
        "pin_memory": device.type == "cuda",
    }
    if opt.num_workers > 0:
        loader_kwargs["persistent_workers"] = True
        loader_kwargs["prefetch_factor"] = opt.prefetch_factor

    print(
        f"[+] Device: {device} / batch_size={opt.batch_size} / "
        f"num_workers={opt.num_workers} / AMP={opt.use_amp and device.type == 'cuda'}"
    )
    print(f"[+] Input mode: {opt.input_mode} / best_metric={opt.best_metric} / weight_decay={opt.weight_decay}")
    train_loader = DataLoader(train_data, batch_size=opt.batch_size, shuffle=True, **loader_kwargs)
    valid_loader = DataLoader(val_data, batch_size=opt.batch_size, shuffle=False, **loader_kwargs)

    # Model Initialization
    model = Srnet()
    model.to(device)
    model = model.apply(weights_init)

    loss_fn = nn.NLLLoss()
    use_amp = opt.use_amp and device.type == "cuda"
    scaler = torch.amp.GradScaler('cuda', enabled=use_amp)
    
    optimizer = torch.optim.Adamax(
        model.parameters(),
        lr=opt.lr,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=opt.weight_decay, 
    )

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=3,
        threshold=5e-5,
        cooldown=1,
    )

    os.makedirs(opt.checkpoints_dir, exist_ok=True)
    best_model_path = os.path.join(opt.checkpoints_dir, "best_srnet_model.pt")
    best_loss_model_path = os.path.join(opt.checkpoints_dir, "best_loss_model.pt")
    best_acc_model_path = os.path.join(opt.checkpoints_dir, "best_acc_model.pt")
    best_balanced_model_path = os.path.join(opt.checkpoints_dir, "best_balanced_model.pt")
    metrics_csv_path = os.path.join(opt.checkpoints_dir, "training_metrics.csv")
    
    check_point = opt.resume_epoch if opt.resume_epoch is not None else latest_checkpoint(opt.checkpoints_dir)
    best_valid_loss = float("inf")
    best_valid_acc = -1.0
    best_balanced_score = -1e9
    min_epochs_before_stop = 25
    patience = 12
    patience_counter = 0

    if not check_point:
        START_EPOCH = 1
        print("[*] 새 모델 학습을 시작합니다. (New Training)")
    else:
        pth = os.path.join(opt.checkpoints_dir, f"net_{check_point}.pt")
        ckpt = torch.load(pth, map_location=device, weights_only=False)
        START_EPOCH = ckpt["epoch"] + 1
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        try:
            scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        except Exception:
            print("[!] 스케줄러 저장 형식 변경 감지: 새 스케줄러로 이어서 학습합니다.")
        best_valid_loss = ckpt.get("best_valid_loss", float("inf"))
        best_valid_acc = ckpt.get("best_valid_acc", ckpt.get("valid_accuracy", -1.0))
        best_balanced_score = ckpt.get("best_balanced_score", -1e9)
        print(f"[*] 에폭 {ckpt['epoch']}부터 학습을 재개합니다. (Resume Training)")

    if os.path.exists(best_model_path):
        best_ckpt = torch.load(best_model_path, map_location=device, weights_only=False)
        best_valid_loss = min(best_valid_loss, best_ckpt.get("best_valid_loss", best_ckpt.get("valid_loss", float("inf"))))
        best_valid_acc = max(best_valid_acc, best_ckpt.get("best_valid_acc", best_ckpt.get("valid_accuracy", -1.0)))
        best_balanced_score = max(best_balanced_score, best_ckpt.get("best_balanced_score", -1e9))

    if START_EPOCH == 1 or not os.path.exists(metrics_csv_path):
        with open(metrics_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "epoch",
                "train_loss",
                "valid_loss",
                "train_accuracy",
                "valid_accuracy",
                "learning_rate",
                "elapsed_seconds",
                "best_metric",
                "balanced_score",
            ])

    training_start_time = time.time()

    try:
        for epoch in range(START_EPOCH, opt.num_epochs + 1):
            training_loss, training_accuracy = [], []
            validation_loss, validation_accuracy = [], []

            # -----------------------------------------
            # Train Phase
            # -----------------------------------------
            model.train()
            # [안전 장치 2] dataset.py가 반환하는 cover/stego 구조에 맞춰 루프 처리
            for i, batch in enumerate(train_loader):
                cover_batch = batch["cover"]
                stego_batch = batch["stego"]

                b_size = cover_batch.size(0)
                
                # 동적으로 현재 배치 크기에 맞춰 Cover=0, Stego=1 라벨 생성
                label_cover = torch.zeros(b_size, dtype=torch.long, device=device)
                label_stego = torch.ones(b_size, dtype=torch.long, device=device)
                
                images = torch.cat((cover_batch, stego_batch), 0).to(device, dtype=torch.float, non_blocking=True)
                labels = torch.cat((label_cover, label_stego), 0)
                
                optimizer.zero_grad(set_to_none=True)
                with torch.amp.autocast('cuda', enabled=use_amp):
                    outputs = model(images)
                    loss = loss_fn(outputs, labels)
                scaler.scale(loss).backward()

                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                
                training_loss.append(loss.item())
                prediction = outputs.data.max(1)[1]
                accuracy = prediction.eq(labels.data).sum() * 100.0 / labels.size(0)
                training_accuracy.append(accuracy.item())

                sys.stdout.write(
                    f"\r Epoch:{epoch}/{opt.num_epochs}"
                    f" Batch:{i+1}/{len(train_loader)}"
                    f" Loss:{training_loss[-1]:.4f}"
                    f" Acc:{training_accuracy[-1]:.2f}"
                    f" LR:{optimizer.param_groups[0]['lr']:.6f}"
                )

            # -----------------------------------------
            # Validation Phase
            # -----------------------------------------
            model.eval()
            with torch.no_grad():
                for i, batch in enumerate(valid_loader):
                    cover_batch = batch["cover"]
                    stego_batch = batch["stego"]

                    b_size = cover_batch.size(0)
                    
                    label_cover = torch.zeros(b_size, dtype=torch.long, device=device)
                    label_stego = torch.ones(b_size, dtype=torch.long, device=device)
                    
                    images = torch.cat((cover_batch, stego_batch), 0).to(device, dtype=torch.float, non_blocking=True)
                    labels = torch.cat((label_cover, label_stego), 0)

                    with torch.amp.autocast('cuda', enabled=use_amp):
                        outputs = model(images)
                        loss = loss_fn(outputs, labels)
                    validation_loss.append(loss.item())
                    
                    prediction = outputs.data.max(1)[1]
                    accuracy = prediction.eq(labels.data).sum() * 100.0 / labels.size(0)
                    validation_accuracy.append(accuracy.item())

            # -----------------------------------------
            # Epoch Metrics & Logging
            # -----------------------------------------
            avg_train_loss = sum(training_loss) / len(training_loss)
            avg_valid_loss = sum(validation_loss) / len(validation_loss)
            avg_train_acc = sum(training_accuracy) / len(training_accuracy)
            avg_valid_acc = sum(validation_accuracy) / len(validation_accuracy)
            generalization_gap = max(0.0, avg_train_acc - avg_valid_acc)
            # Balanced score for edge LSB: accuracy-first, but reject very unstable models.
            # This favors 78~80% candidates while still penalizing high loss and train/valid gap.
            balanced_score = avg_valid_acc - (2.0 * avg_valid_loss) - (0.10 * generalization_gap)

            message = (
                f"Epoch: {epoch}. "
                f"Train Loss:{avg_train_loss:.5f}. Valid Loss:{avg_valid_loss:.5f}. "
                f"Train Acc:{avg_train_acc:.2f} Valid Acc:{avg_valid_acc:.2f}"
            )
            print("\n", message)
            logging.info(message)

            elapsed_seconds = round(time.time() - training_start_time, 2)
            with open(metrics_csv_path, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    epoch,
                    avg_train_loss,
                    avg_valid_loss,
                    avg_train_acc,
                    avg_valid_acc,
                    optimizer.param_groups[0]["lr"],
                    elapsed_seconds,
                    opt.best_metric,
                    balanced_score,
                ])

            scheduler.step(avg_valid_loss)

            state = {
                "epoch": epoch,
                "opt": opt,
                "train_loss": avg_train_loss,
                "valid_loss": avg_valid_loss,
                "train_accuracy": avg_train_acc,
                "valid_accuracy": avg_valid_acc,
                "generalization_gap": generalization_gap,
                "balanced_score": balanced_score,
                "best_valid_acc": max(best_valid_acc, avg_valid_acc),
                "best_balanced_score": max(best_balanced_score, balanced_score),
                "best_metric": opt.best_metric,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "best_valid_loss": min(best_valid_loss, avg_valid_loss),
                "lr": optimizer.param_groups[0]["lr"],
            }

            saver(state, opt.checkpoints_dir, epoch)
            print(f" Checkpoint saved -> {os.path.join(opt.checkpoints_dir, f'net_{epoch}.pt')}")

            improved_loss = avg_valid_loss < best_valid_loss
            improved_acc = avg_valid_acc > best_valid_acc
            improved_balanced = balanced_score > best_balanced_score

            if improved_loss:
                best_valid_loss = avg_valid_loss
                state["best_valid_loss"] = best_valid_loss
                torch.save(state, best_loss_model_path)

            if improved_acc:
                best_valid_acc = avg_valid_acc
                state["best_valid_acc"] = best_valid_acc
                torch.save(state, best_acc_model_path)

            if improved_balanced:
                best_balanced_score = balanced_score
                state["best_balanced_score"] = best_balanced_score
                torch.save(state, best_balanced_model_path)

            if opt.best_metric == "acc":
                improved_main = improved_acc
                main_reason = "Valid Acc 갱신"
            elif opt.best_metric == "balanced":
                improved_main = improved_balanced
                main_reason = "Balanced Score 갱신"
            else:
                improved_main = improved_loss
                main_reason = "Valid Loss 갱신"

            if improved_main:
                patience_counter = 0
                torch.save(state, best_model_path)
                print(
                    f" [BEST] 베스트 모델 저장 완료 ({main_reason}) -> {best_model_path}\n"
                    f"        best_loss={best_valid_loss:.5f}, best_acc={best_valid_acc:.2f}, "
                    f"best_balanced={best_balanced_score:.4f}"
                )
            else:
                patience_counter += 1
                print(
                    f" [경고] 베스트 기준 정체 "
                    f"(metric={opt.best_metric}, 카운트: {patience_counter}/{patience}, "
                    f"최소 학습 에폭: {min_epochs_before_stop})"
                )

                if epoch >= min_epochs_before_stop and patience_counter >= patience:
                    print(f"\n[!] Early Stopping 발동! (에폭 {epoch}) 과적합 방지를 위해 학습을 종료합니다.")
                    break

            del images, labels, outputs, loss
            torch.cuda.empty_cache()
            gc.collect()

    except KeyboardInterrupt:
        print("\n\n[수동 종료 감지] 사용자에 의해 학습이 중단되었습니다.")
        print("[!] 파일 손상을 방지하기 위해 직전 상태를 안전하게 보존했습니다.")
        sys.exit(0)


