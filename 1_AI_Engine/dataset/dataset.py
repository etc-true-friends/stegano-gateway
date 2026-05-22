"""This module provide the data sample for training."""

import os
import random
from typing import Tuple
import torch
from torch import Tensor
from torch.utils.data import Dataset

import imageio.v2 as io  # imageio v2로 업데이트하여 안정성 확보

from opts.options import arguments

opt = arguments()

class DatasetLoad(Dataset):
    """This class returns the data samples."""

    def __init__(
        self,
        cover_path: str,
        stego_path: str,
        size: int,
        transform: Tuple = None,
    ) -> None:
        """Constructor."""
        self.cover = cover_path
        self.stego = stego_path
        self.transforms = transform
        
        valid_extensions = ('.png', '.jpg', '.jpeg', '.pgm')
        
        # 1차 방어선: __init__에서 양쪽에 모두 존재하는 '교집합' 파일만 미리 추려냅니다.
        cover_files = set(f for f in os.listdir(self.cover) if f.lower().endswith(valid_extensions))
        stego_files = set(f for f in os.listdir(self.stego) if f.lower().endswith(valid_extensions))
        
        valid_pairs = cover_files.intersection(stego_files)
        
        self.file_names = sorted(list(valid_pairs))
        self.data_size = min(size, len(self.file_names))
        self.file_names = self.file_names[:self.data_size]

    def __len__(self) -> int:
        """returns the length of the dataset."""
        return self.data_size

    def __getitem__(self, index: int) -> Tuple[Tensor, Tensor]:
        """Returns the (cover, stego) pairs for training with Spatial Augmentation."""
        
        img_name = self.file_names[index]
        cover_path = os.path.join(self.cover, img_name)
        stego_path = os.path.join(self.stego, img_name)
        
        # 2차 방어선: 데이터를 읽으려는 찰나에 파일이 지워졌거나 없다면 다음 인덱스로 건너뜀!
        if not os.path.exists(cover_path) or not os.path.exists(stego_path):
            return self.__getitem__((index + 1) % self.data_size)
        
        cover_img = io.imread(cover_path)
        stego_img = io.imread(stego_path)
        
        # 1. 차원 변경 (HWC -> CHW) 및 Float 텐서 변환 (0~1 정규화)
        cover_tensor = torch.from_numpy(cover_img).permute(2, 0, 1).float() / 255.0
        stego_tensor = torch.from_numpy(stego_img).permute(2, 0, 1).float() / 255.0
        
        # 2. [SRNet 논문 필수 방어막] Spatial Data Augmentation 
        # Cover와 Stego는 한 쌍이므로 '동일한 확률'로 함께 뒤집히고 회전해야 함!
        
        # 랜덤 좌우 반전
        if random.random() > 0.5:
            cover_tensor = torch.flip(cover_tensor, dims=[2])
            stego_tensor = torch.flip(stego_tensor, dims=[2])
            
        # 랜덤 90도 단위 회전 (0도, 90도, 180도, 270도 중 랜덤)
        rot_k = random.choice([0, 1, 2, 3])
        if rot_k > 0:
            cover_tensor = torch.rot90(cover_tensor, k=rot_k, dims=[1, 2])
            stego_tensor = torch.rot90(stego_tensor, k=rot_k, dims=[1, 2])
            
        label1 = torch.tensor(0, dtype=torch.long)
        label2 = torch.tensor(1, dtype=torch.long)
        
        sample = {
            "cover": cover_tensor, 
            "stego": stego_tensor,
            "label": [label1, label2]
        }
        return sample