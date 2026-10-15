import os, sys, yaml, json, random, time, logging
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def get_gpu_info() -> dict:
    info = {"available": torch.cuda.is_available()}
    if info["available"]:
        info["name"] = torch.cuda.get_device_name(0)
        info["total_vram_mb"] = torch.cuda.get_device_properties(0).total_mem / 1e6
        info["allocated_vram_mb"] = torch.cuda.memory_allocated(0) / 1e6
        info["cached_vram_mb"] = torch.cuda.memory_reserved(0) / 1e6
    return info


def setup_logger(name: str, log_path: str, level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    logger.addHandler(ch)
    return logger


class Timer:
    def __init__(self):
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start

    def __str__(self):
        return f"{self.elapsed:.3f}s"


def save_metrics(path: str, metrics: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
