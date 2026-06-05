"""This module provides utility function for training."""
import os
import re
from typing import Any, Dict
import torch
from torch import nn


def saver(state: Dict[str, float], save_dir: str, epoch: int) -> None:
    os.makedirs(save_dir, exist_ok=True)
    torch.save(state, os.path.join(save_dir, f"net_{epoch}.pt"))


def latest_checkpoint(checkpoints_dir: str) -> int:
    """Returns latest net_{epoch}.pt checkpoint epoch."""
    if not os.path.exists(checkpoints_dir):
        return None

    epochs = []
    for filename in os.listdir(checkpoints_dir):
        match = re.fullmatch(r"net_(\d+)\.pt", filename)
        if match:
            epochs.append(int(match.group(1)))

    return max(epochs) if epochs else None


def adjust_learning_rate(optimizer: Any, epoch: int) -> None:
    """Sets the learning rate to the initial learning_rate and decays by 10
    every 30 epochs."""
    learning_rate = optimizer.param_groups[0].get("initial_lr", optimizer.param_groups[0]["lr"]) * (0.1 ** (epoch // 30))
    for param_group in optimizer.param_groups:
        param_group["lr"] = learning_rate


# Weight initialization for conv layers and fc layers
def weights_init(param: Any) -> None:
    """Initializes weights of Conv and fully connected."""

    if isinstance(param, nn.Conv2d):
        torch.nn.init.xavier_uniform_(param.weight.data)
        if param.bias is not None:
            torch.nn.init.constant_(param.bias.data, 0.2)
    elif isinstance(param, nn.Linear):
        torch.nn.init.normal_(param.weight.data, mean=0.0, std=0.01)
        torch.nn.init.constant_(param.bias.data, 0.0)
