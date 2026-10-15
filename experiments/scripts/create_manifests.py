"""
create_manifests.py — G2: Tạo schema manifest rỗng cho ShapeNet, GSO, ảnh tự chụp.

Chỉ tạo header, không thêm dữ liệu. Chạy lại để reset về trạng thái rỗng.
"""
import os, csv, argparse
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = PROJECT_ROOT / "experiments" / "data" / "manifests"
SCRIPT_VERSION = "1.0.0"

MANIFESTS = {
    "dataset_manifest_shapenet.csv": [
        "dataset_source",
        "object_id",
        "class_name",
        "synset_id",
        "mesh_path",
        "image_path",
        "split",
        "selection_reason",
        "seed",
        "created_at",
        "script_version",
    ],
    "gso_manifest.csv": [
        "dataset_source",
        "object_id",
        "class_name",
        "synset_id",
        "mesh_path",
        "image_path",
        "split",
        "selection_reason",
        "seed",
        "created_at",
        "script_version",
    ],
    "real_photos_manifest.csv": [
        "dataset_source",
        "object_id",
        "class_name",
        "synset_id",
        "mesh_path",
        "image_path",
        "split",
        "selection_reason",
        "seed",
        "created_at",
        "script_version",
    ],
    "excluded_samples.csv": [
        "dataset_source",
        "object_id",
        "file_path",
        "exclusion_reason",
        "created_at",
        "script_version",
    ],
}

SUMMARY_HEADER = [
    "dataset_source",
    "class_name",
    "split",
    "object_count",
    "image_count",
    "missing_mesh_count",
    "missing_image_count",
    "render_failed_count",
]


def write_csv(path: str, header: list, rows: list = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        if rows:
            for r in rows:
                writer.writerow(r)


def main():
    parser = argparse.ArgumentParser(description="Create or reset experiment manifest CSVs")
    parser.add_argument("--reset", action="store_true", help="Reset all manifests to empty headers")
    args = parser.parse_args()

    created = []

    for fname, header in MANIFESTS.items():
        path = os.path.join(MANIFEST_DIR, fname)
        write_csv(path, header)
        created.append(fname)

    # dataset_summary.csv: init with zeros for all class/split combos
    summary_rows = []
    shapenet_classes = {
        "chair": "03001627",
        "table": "04379243",
        "lamp": "03636649",
        "bottle": "02876657",
        "mug": "03797390",
    }
    splits = ["train", "validation", "test"]
    for cls_name in shapenet_classes:
        for sp in splits:
            summary_rows.append(["ShapeNetCoreV2", cls_name, sp, 0, 0, 0, 0, 0])

    summary_rows.append(["GSO", "eval", "front", 0, 0, 0, 0, 0])
    summary_rows.append(["RealPhotos", "self_captured", "unassigned", 0, 0, 0, 0, 0])
    write_csv(os.path.join(MANIFEST_DIR, "dataset_summary.csv"), SUMMARY_HEADER, summary_rows)
    created.append("dataset_summary.csv")

    print("Created/reset %d files:" % len(created))
    for f in created:
        path = os.path.join(MANIFEST_DIR, f)
        with open(path, "r", encoding="utf-8-sig") as fh:
            header = fh.readline().strip()
        print("  %s -> %s" % (f, path))
        print("    Header: %s" % header)


if __name__ == "__main__":
    main()
