"""This module provides method to enter various input to the model training."""
import argparse
import os


def arguments():
    """This function returns arguments."""
    parser = argparse.ArgumentParser()

    # 1. 학습/검증 데이터 경로 설정
    parser.add_argument("--cover_path", default="./dataset_real/train/cover")
    parser.add_argument("--stego_path", default="./dataset_real/train/stego")
    parser.add_argument("--valid_cover_path", default="./dataset_real/val/cover")
    parser.add_argument("--valid_stego_path", default="./dataset_real/val/stego")

    parser.add_argument("--checkpoints_dir", default="./checkpoints/")

    # 2. VRAM 보호를 위한 batch size
    parser.add_argument("--batch_size", type=int, default=16)

    # 3. 충분한 학습을 위한 epoch 수
    parser.add_argument("--num_epochs", type=int, default=100)

    # 4. 사용할 데이터 쌍 개수
    parser.add_argument("--train_size", type=int, default=180000)
    parser.add_argument("--val_size", type=int, default=45000)

    # 5. 학습률
    parser.add_argument("--lr", type=float, default=0.001)

    # 5-1. 과적합 완화용 weight decay
    parser.add_argument("--weight_decay", type=float, default=float(os.environ.get("SRNET_WEIGHT_DECAY", "0.0005")))

    # 6. 재개할 체크포인트 epoch
    parser.add_argument("--resume_epoch", type=int, default=None)

    # 7. 입력 전처리 모드
    parser.add_argument(
        "--input_mode",
        choices=["rgb", "lsb"],
        default=os.environ.get("SRNET_INPUT_MODE", "rgb").strip().lower() or "rgb",
        help="rgb: 일반 RGB 입력, lsb: 각 채널의 LSB plane만 입력",
    )

    # 8. Local performance tuning
    parser.add_argument("--num_workers", type=int, default=int(os.environ.get("SRNET_NUM_WORKERS", "8")))
    parser.add_argument("--prefetch_factor", type=int, default=int(os.environ.get("SRNET_PREFETCH_FACTOR", "2")))
    parser.add_argument("--use_amp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cudnn_benchmark", action=argparse.BooleanOptionalAction, default=True)

    # 9. 베스트 모델 저장 기준
    parser.add_argument(
        "--best_metric",
        choices=["loss", "acc", "balanced"],
        default=os.environ.get("SRNET_BEST_METRIC", "loss").strip().lower() or "loss",
        help="loss: Valid Loss 최저, acc: Valid Acc 최고, balanced: Acc/Loss/GAP 균형",
    )

    opt = parser.parse_args()
    return opt
