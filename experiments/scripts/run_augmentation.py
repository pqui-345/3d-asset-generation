import os, sys, argparse, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import torch
from experiments.utils.common import set_seed, load_config, setup_logger, save_metrics

from run_deep import ImageDataset, build_model, get_transforms, DataLoader, nn, optim
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["experiment"]["seed"])
    exp_name = cfg["experiment"]["name"]
    logger = setup_logger(exp_name, f"experiments/outputs/logs/{exp_name}.log")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Device: %s", device)

    train_tfm = get_transforms(cfg, train=True)
    test_tfm = get_transforms(cfg, train=False)

    dataset = ImageDataset(cfg["data"]["manifest"], test_tfm)
    n_classes = len(dataset.le.classes_)

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

    model = build_model("resnet18", n_classes, cfg).to(device)
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

    prec, rec, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average="weighted")
    metrics = {
        "experiment": exp_name,
        "accuracy": float(best_acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "config": cfg["augmentation"],
    }
    logger.info("Final: acc=%.4f prec=%.4f rec=%.4f f1=%.4f", best_acc, prec, rec, f1)
    save_metrics(f"experiments/outputs/metrics/{exp_name}_metrics.json", metrics)


if __name__ == "__main__":
    main()
