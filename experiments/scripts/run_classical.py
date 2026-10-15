import os, sys, argparse, csv, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
from skimage.feature import hog
from PIL import Image

from experiments.utils.common import set_seed, load_config, get_device, setup_logger, Timer, save_metrics


def extract_hog_features(img: Image.Image, cfg: dict) -> np.ndarray:
    img = img.convert("L").resize((224, 224))
    arr = np.array(img, dtype=np.float32)
    hog_cfg = cfg["hog"]
    features = hog(
        arr,
        orientations=hog_cfg["orientations"],
        pixels_per_cell=tuple(hog_cfg["pixels_per_cell"]),
        cells_per_block=tuple(hog_cfg["cells_per_block"]),
        block_norm=hog_cfg["block_norm"],
        feature_vector=True,
    )
    return features


def load_dataset(manifest_path: str, label_col: str = "label"):
    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    X, y = [], []
    for r in rows:
        img_path = r.get("image_path", "")
        if img_path and os.path.exists(img_path):
            img = Image.open(img_path)
            X.append(img)
            y.append(r[label_col])
    return X, y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/configs/classical.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["experiment"]["seed"])
    logger = setup_logger("classical", "experiments/outputs/logs/classical.log")

    logger.info("Loading dataset from %s", cfg["data"]["manifest"])
    images, labels_str = load_dataset(cfg["data"]["manifest"])

    if len(images) == 0:
        logger.error("No images found. Run build_dataset_manifest.py --render first.")
        return

    le = LabelEncoder()
    y = le.fit_transform(labels_str)
    n_classes = len(le.classes_)
    logger.info("Loaded %d samples, %d classes", len(images), n_classes)

    logger.info("Extracting HOG features...")
    X = []
    for img in images:
        X.append(extract_hog_features(img, cfg))
    X = np.array(X)
    logger.info("Feature matrix shape: %s", X.shape)

    cv = StratifiedKFold(n_splits=cfg["eval"]["cv_folds"], shuffle=True, random_state=cfg["experiment"]["seed"])
    metrics_list = []

    for model_name, clf_fn in [("svm", lambda: SVC(**cfg["svm"], probability=True, random_state=cfg["experiment"]["seed"])),
                                ("rf", lambda: RandomForestClassifier(**cfg["rf"], random_state=cfg["experiment"]["seed"]))]:
        logger.info("=== %s ===", model_name.upper())
        fold_scores = {"accuracy": [], "precision": [], "recall": [], "f1": []}

        for fold, (train_idx, test_idx) in enumerate(cv.split(X, y)):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            clf = clf_fn()
            with Timer() as t:
                clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)

            acc = accuracy_score(y_test, y_pred)
            prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted")

            fold_scores["accuracy"].append(acc)
            fold_scores["precision"].append(prec)
            fold_scores["recall"].append(rec)
            fold_scores["f1"].append(f1)
            logger.info("  Fold %d | acc=%.4f prec=%.4f rec=%.4f f1=%.4f | time=%s",
                        fold + 1, acc, prec, rec, f1, t)

        summary = {k: {"mean": float(np.mean(v)), "std": float(np.std(v))} for k, v in fold_scores.items()}
        logger.info("  %s CV summary: %s", model_name.upper(), json.dumps(summary, indent=2))
        metrics_list.append({"model": model_name, **summary})

    save_metrics(cfg["experiment"]["output_dir"] + "/metrics/classical_metrics.json", {"results": metrics_list})
    logger.info("Done. Metrics saved.")


if __name__ == "__main__":
    main()
