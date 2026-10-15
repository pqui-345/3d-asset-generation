import os, sys, sqlite3, csv, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from PIL import Image
import trimesh


TEMPLATE_DIRS = [
    "static/templates/core_100",
    "static/templates/objaverse_ext",
]
SQLITE_PATH = "data/template_metadata.sqlite"
OUTPUT_MANIFEST = "experiments/data/manifests/dataset_manifest.csv"
OUTPUT_IMAGE_DIR = "experiments/data/images"
RENDER_SIZE = 224


def extract_category(name: str) -> str:
    name_lower = name.lower()
    cat_map = [
        ("animal", ["animal", "fish", "bird", "cat", "dog", "horse", "sculpin",
                     "crab", "lobster", "shrimp", "shell", "skull", "head"]),
        ("architecture", ["architecture", "building", "house", "tower", "bridge",
                          "acropolis", "gate", "monument", "ruin", "castle"]),
        ("furniture", ["chair", "table", "desk", "bench", "cabinet", "shelf",
                       "sofa", "couch", "bed", "drawer", "stool", "rack"]),
        ("vehicle", ["car", "truck", "bus", "train", "airplane", "plane",
                     "boat", "ship", "bicycle", "motorcycle", "wagon"]),
        ("tool", ["tool", "hammer", "screwdriver", "wrench", "knife", "scissor",
                  "axe", "saw", "drill", "pliers", "key", "lock"]),
        ("vessel_container", ["cup", "bottle", "bowl", "plate", "vase", "jar",
                              "pot", "bucket", "can", "glass", "mug", "pitcher"]),
        ("electronics", ["camera", "phone", "monitor", "screen", "radio",
                         "speaker", "laptop", "keyboard", "robot"]),
        ("food", ["food", "fruit", "vegetable", "cake", "bread", "cheese",
                  "meat", "pizza", "hamburger", "donut"]),
        ("clothing", ["shoe", "boot", "hat", "helmet", "glove", "bag",
                      "backpack", "suitcase", "watch", "ring"]),
        ("musical_instrument", ["guitar", "piano", "drum", "violin", "flute",
                                "trumpet", "horn", "harp"]),
        ("sport", ["ball", "racket", "bat", "frisbee", "kite", "skate",
                   "surfboard", "snowboard"]),
        ("medical", ["medical", "bone", "tooth", "heart", "brain", "skeleton",
                     "anatomy", "cell", "dna"]),
        ("natural_object", ["rock", "stone", "tree", "plant", "flower", "leaf",
                            "crystal", "gem", "mountain", "volcano"]),
        ("educational", ["educational", "globe", "map", "book", "molecule",
                         "atom", "gear", "pulley", "lever", "prism"]),
        ("decoration", ["decoration", "ornament", "statue", "figurine", "doll",
                        "toy", "lamp", "candle", "mirror"]),
    ]
    for cat, keywords in cat_map:
        for kw in keywords:
            if kw in name_lower:
                return cat
    return "other"


def render_front_view(glb_path: str, size: int = 224) -> Image.Image:
    try:
        scene = trimesh.load(glb_path, force="scene")
        if isinstance(scene, trimesh.Trimesh):
            scene = trimesh.Scene(scene)

        bounds = scene.bounds
        center = bounds.mean(axis=0)
        extent = bounds.ptp(axis=0).max()
        if extent == 0:
            extent = 1.0

        camera_distance = extent * 2.5
        scene.camera_transform = trimesh.scene.cameras.look_at(
            scene,
            center=center,
            distance=camera_distance,
        )

        data = scene.save_image(resolution=(size, size), visible=True)
        return Image.fromarray(data).convert("RGB")
    except Exception:
        return Image.new("RGB", (size, size), (128, 128, 128))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="Render 2D views from GLB files")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples")
    args = parser.parse_args()

    conn = sqlite3.connect(Path(__file__).resolve().parents[2] / SQLITE_PATH)
    templates = conn.execute("SELECT uid, name, category, glb_path FROM templates").fetchall()
    conn.close()

    if args.limit:
        templates = templates[:args.limit]

    os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_MANIFEST), exist_ok=True)

    rows = []
    for idx, (uid, name, cat, glb_path) in enumerate(templates):
        label = extract_category(name) if cat in ("educational", None, "") else cat
        print(f"[{idx+1}/{len(templates)}] {uid[:8]}... name='{name[:40]}' -> label='{label}'")

        if args.render:
            glb_full = Path(__file__).resolve().parents[2] / glb_path
            if glb_full.exists():
                img = render_front_view(str(glb_full), RENDER_SIZE)
                img_path = os.path.join(OUTPUT_IMAGE_DIR, f"{uid}_front.png")
                img.save(img_path)
            else:
                img_path = ""
        else:
            img_path = ""

        rows.append({
            "uid": uid,
            "name": name,
            "category_orig": cat or "",
            "label": label,
            "glb_path": glb_path,
            "image_path": img_path,
            "source": "objaverse",
        })

    with open(OUTPUT_MANIFEST, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    labels = set(r["label"] for r in rows)
    print(f"\nManifest saved: {OUTPUT_MANIFEST}")
    print(f"Total samples: {len(rows)}")
    print(f"Number of classes: {len(labels)}")
    print(f"Classes: {sorted(labels)}")


if __name__ == "__main__":
    main()
