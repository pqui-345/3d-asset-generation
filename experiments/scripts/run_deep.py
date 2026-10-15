import os, sys, argparse, csv, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from PIL import Image

from experiments.utils.common import set_seed, load_config, get_device, setup_logger, Timer, save_metrics


class ImageDataset(Dataset):
    def __init__(self, manifest_path: str, transform, label_col: str = "label"):
        with open(manifest_path, "r", encoding="utf-8-sig") as f:
            self.rows = [r for r in csv.DictReader(f) if r.get("image_path") and os.path.exists(r["image_path"])]
        self.transform = transform
        self.labels_str = [r[label_col] for r in self.rows]
        self.le = LabelEncoder().fit(self.labels_str)
        self.labels = self.le.transform(self.labels_str)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        img = Image.open(self.rows[idx]["image_path"]).convert("RGB")
        return self.transform(img), self.labels[idx]


def build_model(arch: str, n_classes: int, cfg: dict):
    mcfg = cfg["model"]
    if arch == "resnet18":
        model = models.resnet18(weights="IMAGENET1K_V1" if mcfg["pretrained"] else None)
        in_features = model.fc.in_features
        if mcfg["freeze_backbone"]:
            for param in model.parameters():
                param.requires_grad = False
        model.fc = nn.Sequential(
            nn.Dropout(mcfg.get("dropout", 0.3)),
            nn.Linear(in_features, n_classes),
        )
    elif arch == "vit":
        from transformers import ViTForImageClassification
        model = ViTForImageClassification.from_pretrained(
            mcfg["checkpoint"],
            num_labels=n_classes,
            ignore_mismatched_sizes=True,
        )
        if mcfg["freeze_backbone"]:
            for param in model.vit.parameters():
                param.requires_grad = False
    else:
        raise ValueError(f"Unknown architecture: {arch}")
    return model


def get_transforms(cfg: dict, train: bool = True):
    dcfg = cfg["data"]
    size = dcfg["input_size"]
    t = [transforms.Resize((size, size))]
    if train and "augmentation" in cfg:
        acfg = cfg["augmentation"]["train"]
        if acfg.get("random_horizontal_flip"):
            t.append(transforms.RandomHorizontalFlip(acfg["random_horizontal_flip"]))
        if acfg.get("random_rotation"):
            t.append(transforms.RandomRotation(acfg["random_rotation"]))
        if acfg.get("color_jitter"):
            t.append(transforms.ColorJitter(*acfg["color_jitter"]))
        if acfg.get("random_affine"):
            aff = acfg["random_affine"]
            t.append(transforms.RandomAffine(aff[0], translate=tuple(aff[1]) if len(aff) > 1 else None))
    t.append(transforms.ToTensor())
    t.append(transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]))
    return transforms.Compose(t)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["experiment"]["seed"])
    exp_name = cfg["experiment"]["name"]
    logger = setup_logger(exp_name, f"experiments/outputs/logs/{exp_name}.log")
    device = get_device()
    logger.info("Device: %s", device)

    train_tfm = get_transforms(cfg, train=True)
    test_tfm = get_transforms(cfg, train=False)

    dataset = ImageDataset(cfg["data"]["manifest"], test_tfm)
    n_classes = len(dataset.le.classes_)
    logger.info("Loaded %d samples, %d classes", len(dataset), n_classes)

    n = len(dataset)
    n_train = int(n * 0.8)
    n_test = n - n_train
    train_ds, test_ds = torch.utils.data.random_split(
        dataset, [n_train, n_test],
        generator=torch.Generator().manual_seed(cfg["experiment"]["seed"]),
    )
    train_ds.dataset.transform = train_tfm

    train_loader = DataLoader(train_ds, batch_size=cfg["data"]["batch_size"], shuffle=True, num_workers=cfg["data"]["num_workers"])
    test_loader = DataLoader(test_ds, batch_size=cfg["data"]["batch_size"], shuffle=False, num_workers=cfg["data"]["num_workers"])

    model = build_model(cfg["model"]["architecture"], n_classes, cfg).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                            lr=cfg["train"]["lr"], weight_decay=cfg["train"]["weight_decay"])
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg["train"]["epochs"])

    best_acc = 0.0
    patience_counter = 0
    for epoch in range(cfg["train"]["epochs"]):
        model.train()
        train_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            if isinstance(outputs, dict):
                outputs = outputs.logits
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        scheduler.step()

        model.eval()
        all_preds, all_labels = [], []
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                if isinstance(outputs, dict):
                    outputs = outputs.logits
                _, preds = torch.max(outputs, 1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        acc = accuracy_score(all_labels, all_preds)
        logger.info("Epoch %3d/%d | loss=%.4f | val_acc=%.4f", epoch + 1, cfg["train"]["epochs"], train_loss / len(train_loader), acc)

        if acc > best_acc:
            best_acc = acc
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= cfg["train"]["early_stop_patience"]:
                logger.info("Early stopping at epoch %d", epoch + 1)
                break

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    prec, rec, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average="weighted")
    conf = confusion_matrix(all_labels, all_preds)

    metrics = {
        "experiment": exp_name,
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "confusion_matrix": conf.tolist(),
        "classes": dataset.le.classes_.tolist(),
    }
    logger.info("Final: acc=%.4f prec=%.4f rec=%.4f f1=%.4f", acc, prec, rec, f1)
    save_metrics(f"experiments/outputs/metrics/{exp_name}_metrics.json", metrics)


if __name__ == "__main__":
    main()
