"""This module provides method to enter various input to the model training."""
import argparse

def arguments():
    """This function returns arguments."""
    parser = argparse.ArgumentParser()
    
    # 1. 진짜 야생 데이터(수능 킬러 문항) 경로 설정
    parser.add_argument("--cover_path", default="./dataset_real/train/cover")
    parser.add_argument("--stego_path", default="./dataset_real/train/stego")
    parser.add_argument("--valid_cover_path", default="./dataset_real/val/cover")
    parser.add_argument("--valid_stego_path", default="./dataset_real/val/stego")
    
    parser.add_argument("--checkpoints_dir", default="./checkpoints/")
    
    # 2. VRAM 보호를 위한 Batch Size (중복 제거 완료: 16으로 안전하게 설정)
    parser.add_argument("--batch_size", type=int, default=16)
    
    # 3. 충분한 학습을 위해 에포크 상향
    parser.add_argument("--num_epochs", type=int, default=100)
    
    # 4. 데이터 사이즈 명시 (자투리 버림 적용)
    parser.add_argument("--train_size", type=int, default=180000)
    parser.add_argument("--val_size", type=int, default=45000)
    
    # 5. 학습률(Learning Rate)
    parser.add_argument("--lr", type=float, default=0.001)

    opt = parser.parse_args()
    return opt