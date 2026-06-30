"""Dataset loader for paired cover/stego images."""

import os
import random
from typing import Tuple

import numpy as np
import torch
from torch import Tensor
from torch.utils.data import Dataset
from PIL import Image


class DatasetLoad(Dataset):
    """Returns paired cover/stego samples."""

    def __init__(
        self,
        cover_path: str,
        stego_path: str,
        size: int,
        transform: Tuple = None,
        image_size: int = 256,
        input_mode: str = "rgb",
    ) -> None:
        self.cover = cover_path
        self.stego = stego_path
        self.transforms = transform
        self.image_size = image_size
        self.input_mode = (input_mode or "rgb").strip().lower()
        if self.input_mode not in {"rgb", "lsb"}:
            raise ValueError(f"지원하지 않는 input_mode 입니다: {self.input_mode}")

        if not os.path.isdir(self.cover):
            raise FileNotFoundError(f"Cover 폴더를 찾을 수 없습니다: {self.cover}")
        if not os.path.isdir(self.stego):
            raise FileNotFoundError(f"Stego 폴더를 찾을 수 없습니다: {self.stego}")

        valid_extensions = (".png", ".jpg", ".jpeg", ".pgm")
        cover_files = {
            f for f in os.listdir(self.cover)
            if f.lower().endswith(valid_extensions)
        }
        stego_files = {
            f for f in os.listdir(self.stego)
            if f.lower().endswith(valid_extensions)
        }

        valid_pairs = cover_files.intersection(stego_files)
        self.file_names = sorted(valid_pairs)
        self.data_size = min(size, len(self.file_names))
        self.file_names = self.file_names[:self.data_size]

    def __len__(self) -> int:
        return self.data_size

    def _to_tensor(self, arr: np.ndarray) -> Tensor:
        if self.input_mode == "lsb":
            arr = (arr.astype(np.uint8) & 1).astype(np.float32)
            return torch.from_numpy(arr).permute(2, 0, 1)
        return torch.from_numpy(arr).permute(2, 0, 1).float() / 255.0

    def _read_image(self, path: str) -> Tensor:
        with Image.open(path) as img:
            img = img.convert("RGB")
            if img.size != (self.image_size, self.image_size):
                resample = Image.Resampling.NEAREST if self.input_mode == "lsb" else Image.Resampling.BILINEAR
                img = img.resize((self.image_size, self.image_size), resample)

            if self.transforms is not None and self.input_mode == "rgb":
                return self.transforms(img)

            arr = np.array(img)
            return self._to_tensor(arr)

    def __getitem__(self, index: int) -> Tuple[Tensor, Tensor]:
        if self.data_size == 0:
            raise IndexError("학습 가능한 cover/stego 쌍이 없습니다.")

        img_name = self.file_names[index]
        cover_path = os.path.join(self.cover, img_name)
        stego_path = os.path.join(self.stego, img_name)

        if not os.path.exists(cover_path) or not os.path.exists(stego_path):
            return self.__getitem__((index + 1) % self.data_size)

        cover_tensor = self._read_image(cover_path)
        stego_tensor = self._read_image(stego_path)

        if random.random() > 0.5:
            cover_tensor = torch.flip(cover_tensor, dims=[2])
            stego_tensor = torch.flip(stego_tensor, dims=[2])

        rot_k = random.choice([0, 1, 2, 3])
        if rot_k > 0:
            cover_tensor = torch.rot90(cover_tensor, k=rot_k, dims=[1, 2])
            stego_tensor = torch.rot90(stego_tensor, k=rot_k, dims=[1, 2])

        return {
            "cover": cover_tensor,
            "stego": stego_tensor,
            "label": [
                torch.tensor(0, dtype=torch.long),
                torch.tensor(1, dtype=torch.long),
            ],
        }
