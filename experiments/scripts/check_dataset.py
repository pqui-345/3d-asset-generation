"""
check_dataset.py — G2: Kiểm tra trạng thái dataset hiện có.

Báo chính xác dung lượng, số file, trạng thái từng dataset.
Không tự ý sửa dữ liệu.
"""
import os, csv, json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = PROJECT_ROOT / "experiments" / "data" / "manifests"

# Đường dẫn dự kiến cho các dataset
EXPECTED_PATHS = {
    "ShapeNetCoreV2": {
        "root": str(PROJECT_ROOT / "experiments" / "data" / "ShapeNetCore.v2"),
        "synsets": {
            "03001627": "chair",
            "04379243": "table",
            "03636649": "lamp",
            "02876657": "bottle",
            "03797390": "mug",
        },
        "expected_per_class": 200,
    },
    "GSO": {
        "root": str(PROJECT_ROOT / "static" / "templates" / "gso"),
        "expected_count": 300,
        "manifest_url": "https://raw.githubusercontent.com/google-research/google-scanned-objects/master/manifest.txt",
    },
    "RealPhotos": {
        "root": str(PROJECT_ROOT / "data" / "real_photos"),
        "expected_count": None,
    },
}

REQUIRED_FREE_SPACE_GB = {
    "ShapeNetCoreV2_subset": 5,
    "GSO_full": 3,
    "ShapeNetCoreV2_full_download": 50,
}


def get_free_space_gb(path: str) -> float:
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        return free / (1024 ** 3)
    except Exception:
        return 0.0


def check_shapenet(path: str) -> dict:
    result = {
        "status": "NOT_DOWNLOADED",
        "root_exists": os.path.isdir(path),
        "classes_found": {},
        "total_models": 0,
        "total_meshes_valid": 0,
        "total_images": 0,
    }
    if not result["root_exists"]:
        return result

    synsets = EXPECTED_PATHS["ShapeNetCoreV2"]["synsets"]
    for sid, cls_name in synsets.items():
        cls_dir = os.path.join(path, sid)
        if not os.path.isdir(cls_dir):
            result["classes_found"][cls_name] = {"status": "NOT_FOUND", "models": 0, "meshes_valid": 0}
            continue

        model_ids = [d for d in os.listdir(cls_dir) if os.path.isdir(os.path.join(cls_dir, d))]
        valid_meshes = 0
        images = 0
        for mid in model_ids:
            model_dir = os.path.join(cls_dir, mid, "models")
            if os.path.isdir(model_dir):
                obj_path = os.path.join(model_dir, "model_normalized.obj")
                if os.path.isfile(obj_path) and os.path.getsize(obj_path) > 0:
                    valid_meshes += 1
            img_dir = os.path.join(cls_dir, mid, "images")
            if os.path.isdir(img_dir):
                images += len([f for f in os.listdir(img_dir) if f.endswith((".png", ".jpg"))])

        result["classes_found"][cls_name] = {
            "status": "OK" if valid_meshes > 0 else "NO_VALID_MESHES",
            "models": len(model_ids),
            "meshes_valid": valid_meshes,
            "images": images,
        }
        result["total_models"] += len(model_ids)
        result["total_meshes_valid"] += valid_meshes
        result["total_images"] += images

    if result["total_meshes_valid"] > 0:
        result["status"] = "PARTIAL"
        if result["total_meshes_valid"] >= 1000:
            result["status"] = "READY"
    return result


def check_gso(path: str) -> dict:
    result = {
        "status": "NOT_DOWNLOADED",
        "root_exists": os.path.isdir(path),
        "object_dirs": 0,
        "glb_files": 0,
        "obj_files": 0,
        "texture_files": 0,
        "metadata_files": 0,
        "images": 0,
        "total_size_mb": 0,
    }
    if not result["root_exists"]:
        return result

    if not os.path.isdir(path):
        return result

    total_glb = 0
    total_obj = 0
    total_tex = 0
    total_meta = 0
    total_img = 0
    total_size = 0
    obj_dirs = 0

    for d in os.listdir(path):
        obj_dir = os.path.join(path, d)
        if not os.path.isdir(obj_dir):
            continue
        obj_dirs += 1

        glb = os.path.join(obj_dir, "model.glb")
        if os.path.isfile(glb):
            total_glb += 1
            total_size += os.path.getsize(glb)

        objf = os.path.join(obj_dir, "model.obj")
        if os.path.isfile(objf):
            total_obj += 1

        tex = os.path.join(obj_dir, "texture.png")
        if os.path.isfile(tex):
            total_tex += 1
            total_size += os.path.getsize(tex)

        meta = os.path.join(obj_dir, "metadata.json")
        if os.path.isfile(meta):
            total_meta += 1

        render = os.path.join(obj_dir, "renders", "front.png")
        if os.path.isfile(render):
            total_img += 1

    result["object_dirs"] = obj_dirs
    result["glb_files"] = total_glb
    result["obj_files"] = total_obj
    result["texture_files"] = total_tex
    result["metadata_files"] = total_meta
    result["images"] = total_img
    result["total_size_mb"] = total_size / 1e6

    if total_glb > 0:
        result["status"] = "PARTIAL"
        if total_glb >= 300:
            result["status"] = "READY"
    return result


def check_real_photos(path: str) -> dict:
    result = {
        "status": "NOT_DOWNLOADED",
        "root_exists": os.path.isdir(path),
        "subdirs": 0,
        "images": 0,
    }
    if not result["root_exists"]:
        return result

    result["subdirs"] = len([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
    result["images"] = len([f for f in os.listdir(path) if f.endswith((".png", ".jpg", ".jpeg"))])
    if result["images"] > 0:
        result["status"] = "PARTIAL"
    return result


def format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    else:
        return f"{n / (1024 * 1024):.1f} MB"


def main():
    print("=" * 70)
    print("G2 — Dataset Status Check")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Script root: {PROJECT_ROOT}")
    print("=" * 70)

    free_e = get_free_space_gb(str(PROJECT_ROOT))
    print(f"\nDisk space on E: {free_e:.1f} GB free\n")

    # Kiểm tra từng dataset
    for ds_name, info in EXPECTED_PATHS.items():
        root = info["root"]
        print(f"\n--- {ds_name} ---")
        print(f"  Expected path: {root}")
        print(f"  Path exists:   {os.path.isdir(root)}")

        if ds_name == "ShapeNetCoreV2":
            status = check_shapenet(root)
            print(f"  Status:        {status['status']}")
            print(f"  Root exists:   {status['root_exists']}")
            for cls_name, cls_info in status["classes_found"].items():
                print(f"    {cls_name}: {cls_info}")
            print(f"  Total models:   {status['total_models']}")
            print(f"  Meshes valid:   {status['total_meshes_valid']}")
            print(f"  Images found:   {status['total_images']}")

        elif ds_name == "GSO":
            status = check_gso(root)
            print(f"  Status:        {status['status']}")
            print(f"  Object dirs:   {status['object_dirs']}")
            print(f"  GLB files:     {status['glb_files']}")
            print(f"  OBJ files:     {status['obj_files']}")
            print(f"  Textures:      {status['texture_files']}")
            print(f"  Renders:       {status['images']}")
            print(f"  Total size:    {status['total_size_mb']:.0f} MB")

        elif ds_name == "RealPhotos":
            status = check_real_photos(root)
            print(f"  Status:        {status['status']}")
            print(f"  Subdirs:       {status['subdirs']}")
            print(f"  Images:        {status['images']}")

    print(f"\n{'=' * 70}")
    print("Space requirements:")
    for what, gb in REQUIRED_FREE_SPACE_GB.items():
        ok = "OK" if free_e >= gb else "INSUFFICIENT"
        print(f"  {what}: ~{gb} GB  [{ok}]")
    print(f"{'=' * 70}")

    print(f"\nManifest files in {MANIFEST_DIR}:")
    if os.path.isdir(str(MANIFEST_DIR)):
        for fname in sorted(os.listdir(str(MANIFEST_DIR))):
            fp = os.path.join(str(MANIFEST_DIR), fname)
            size = os.path.getsize(fp)
            with open(fp, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
            print(f"  {fname:<45} {format_bytes(size):>10}  {len(lines)} lines")


if __name__ == "__main__":
    main()
