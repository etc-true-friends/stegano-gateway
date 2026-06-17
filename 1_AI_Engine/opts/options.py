"""This module provides method to enter various input to the model training."""
import argparse

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

    # 6. 재개할 체크포인트 epoch
    parser.add_argument("--resume_epoch", type=int, default=None)
    

    # 7. Local performance tuning
    parser.add_argument("--num_workers", type=int, default=8)
    parser.add_argument("--prefetch_factor", type=int, default=4)
    parser.add_argument("--use_amp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cudnn_benchmark", action=argparse.BooleanOptionalAction, default=True)
    opt = parser.parse_args()
    return opt


