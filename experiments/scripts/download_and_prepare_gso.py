#!/usr/bin/env python3
"""
download_and_prepare_gso.py — G2: Download, validate, and render
Google Scanned Objects (GSO) from Gazebo Fuel for TripoSR evaluation.

Modes:
  --list                     List available object IDs, no download
  --select --count N --seed S  Select N object IDs deterministically
  --download                 Download selected object zip files
  --validate                 Check GLB integrity
  --render                   Render front views via trimesh+pyglet
  --all --confirm-download   Run full pipeline (must opt-in)
  --dry-run                  Show what would be done
  --limit N                  Limit processing to N objects
  --base-dir PATH            Override project root
  --reset-manifest           Reset gso_manifest.csv before adding
"""

import io, json, os, csv, sys, time, hashlib, shutil, zipfile, random, re
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import numpy as np

try:
    import requests
except ImportError:
    requests = None

try:
    import trimesh
except ImportError:
    trimesh = None

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT_VERSION = "1.0.0"
SCRIPT_NAME = "download_and_prepare_gso.py"

# --- Default paths ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = PROJECT_ROOT / "experiments" / "data" / "manifests"
GSO_DIR = PROJECT_ROOT / "static" / "templates" / "gso"
LOG_DIR = PROJECT_ROOT / "experiments" / "logs"
MANIFEST_PATH = MANIFEST_DIR / "gso_manifest.csv"
EXCLUDED_PATH = MANIFEST_DIR / "excluded_samples.csv"
SUMMARY_PATH = MANIFEST_DIR / "dataset_summary.csv"
SELECTED_IDS_PATH = MANIFEST_DIR / "gso_selected_ids.csv"

# --- API ---
FUEL_API = "https://fuel.gazebosim.org/1.0"
FUEL_WEB = "https://fuel.gazebosim.org"
GSO_OWNER = "GoogleResearch"
PER_PAGE = 100
DOWNLOAD_TIMEOUT = 300
DOWNLOAD_RETRIES = 3

# --- Render ---
RENDER_SIZE = 512
CAMERA_DISTANCE_FACTOR = 2.5

MANIFEST_HEADER = [
    "dataset_source", "object_id", "class_name", "synset_id",
    "mesh_path", "image_path", "split", "selection_reason",
    "seed", "created_at", "script_version",
]
EXCLUDED_HEADER = [
    "dataset_source", "object_id", "file_path",
    "exclusion_reason", "created_at", "script_version",
]


# ---------------------------------------------------------------------------
#   Helpers
# ---------------------------------------------------------------------------

def log_msg(msg: str):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_bytes(n: int) -> str:
    if n < 1024:
        return "%d B" % n
    elif n < 1024 ** 2:
        return "%.1f KB" % (n / 1024)
    else:
        return "%.1f MB" % (n / (1024 ** 2))


def safe_obj_id(raw_name: str) -> str:
    oid = raw_name.strip().replace("/", "_").replace("\\", "_")
    oid = re.sub(r"[^a-zA-Z0-9_\-]", "_", oid)
    return oid.strip("_")


# ---------------------------------------------------------------------------
#   Mode: --list
# ---------------------------------------------------------------------------

def list_objects(args) -> list:
    if requests is None:
        log_msg("ERROR: requests library required for --list")
        return []

    all_models = []
    page = 1
    while True:
        url = "%s/models?owner=%s&page=%d&per_page=%d" % (FUEL_API, GSO_OWNER, page, PER_PAGE)
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        except Exception as e:
            log_msg("ERROR: API request failed at page %d: %s" % (page, e))
            break
        if r.status_code != 200:
            log_msg("ERROR: API returned %d at page %d" % (r.status_code, page))
            break
        data = r.json()
        if not data:
            break
        filtered = [m for m in data if m.get("owner") == GSO_OWNER]
        all_models.extend(filtered)
        if len(data) < PER_PAGE:
            break
        page += 1

    log_msg("Found %d objects owned by %s" % (len(all_models), GSO_OWNER))
    total_size_gb = sum(m["filesize"] for m in all_models) / (1024 ** 3)
    log_msg("Total size of all objects: %.2f GB" % total_size_gb)

    out_path = MANIFEST_DIR / "gso_all_objects.json"
    os.makedirs(str(MANIFEST_DIR), exist_ok=True)
    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(all_models, f, indent=2)
    log_msg("Saved full object list to %s" % out_path)

    return all_models


# ---------------------------------------------------------------------------
#   Mode: --select
# ---------------------------------------------------------------------------

def select_objects(objects: list, args) -> list:
    count = args.count or 300
    seed = args.seed or 42

    object_ids = sorted([m["name"] for m in objects if m.get("owner") == GSO_OWNER])
    log_msg("Total available object IDs (sorted): %d" % len(object_ids))

    if count > len(object_ids):
        log_msg("WARNING: Requested %d but only %d available, using %d" % (count, len(object_ids), len(object_ids)))
        count = len(object_ids)

    rng = random.Random(seed)
    selected = rng.sample(object_ids, count)
    selected.sort()

    os.makedirs(str(MANIFEST_DIR), exist_ok=True)
    with open(str(SELECTED_IDS_PATH), "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["selection_order", "object_id", "seed", "script_version", "created_at"])
        now = now_str()
        for i, oid in enumerate(selected):
            writer.writerow([i + 1, oid, seed, SCRIPT_VERSION, now])

    log_msg("Selected %d object IDs (seed=%d)" % (count, seed))
    log_msg("Saved to %s" % SELECTED_IDS_PATH)
    return selected


# ---------------------------------------------------------------------------
#   Mode: --download
# ---------------------------------------------------------------------------

def download_objects(selected_ids: list, args):
    if requests is None:
        log_msg("ERROR: requests library required for --download")
        return

    if not selected_ids:
        log_msg("No object IDs to download. Run --select first or provide --selected-ids")
        return

    limit = args.limit or len(selected_ids)
    selected_ids = selected_ids[:limit]
    log_msg("Will download %d objects" % len(selected_ids))

    succeeded = 0
    failed = 0
    total_bytes = 0
    skipped = 0

    for idx, oid in enumerate(selected_ids):
        obj_dir = GSO_DIR / safe_obj_id(oid)
        glb_path = obj_dir / "model.glb"
        meta_path = obj_dir / "metadata.json"

        if glb_path.exists() and glb_path.stat().st_size > 0:
            log_msg("  [%d/%d] %s: already exists, skipping" % (idx + 1, len(selected_ids), oid))
            skipped += 1
            total_bytes += glb_path.stat().st_size
            continue

        url = "%s/%s/models/%s.zip" % (FUEL_API, GSO_OWNER, quote(oid, safe=""))
        log_msg("  [%d/%d] %s: downloading %s ..." % (idx + 1, len(selected_ids), oid, format_bytes(
            next((m["filesize"] for m in load_all_objects_cached() if m["name"] == oid), 0))))

        temp_zip = obj_dir / ".download.part"
        os.makedirs(str(obj_dir), exist_ok=True)

        success = False
        for attempt in range(DOWNLOAD_RETRIES):
            try:
                r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True,
                                 headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
                if r.status_code != 200:
                    log_msg("    attempt %d: HTTP %d" % (attempt + 1, r.status_code))
                    time.sleep(2)
                    continue
                with open(str(temp_zip), "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                success = True
                break
            except Exception as e:
                log_msg("    attempt %d failed: %s" % (attempt + 1, e))
                time.sleep(5)

        if not success:
            log_msg("  FAILED: download exhausted retries")
            record_exclusion(GSO_OWNER, oid, str(temp_zip) if temp_zip.exists() else "", "download_failed")
            if temp_zip.exists():
                temp_zip.unlink()
            failed += 1
            continue

        zip_size = temp_zip.stat().st_size
        if zip_size < 100:
            log_msg("  FAILED: zip too small (%d bytes)" % zip_size)
            record_exclusion(GSO_OWNER, oid, str(temp_zip), "empty_file")
            temp_zip.unlink()
            failed += 1
            continue

        try:
            with zipfile.ZipFile(str(temp_zip), "r") as zf:
                names = zf.namelist()
                original_format = None
                mesh_source_path = None
                converted = False

                glb_in_zip = [n for n in names if n.endswith(".glb")]
                obj_in_zip = [n for n in names if n.endswith(".obj") and "meshes" in n]
                dae_in_zip = [n for n in names if n.endswith(".dae")]

                if glb_in_zip:
                    original_format = "glb"
                    mesh_source_path = glb_in_zip[0]
                    mesh_data = zf.read(mesh_source_path)
                    with open(str(glb_path), "wb") as f:
                        f.write(mesh_data)
                    total_bytes += glb_path.stat().st_size

                elif obj_in_zip:
                    original_format = "obj"
                    mesh_source_path = obj_in_zip[0]
                    obj_data = zf.read(mesh_source_path)
                    obj_path = obj_dir / "model.obj"
                    with open(str(obj_path), "wb") as f:
                        f.write(obj_data)

                    mtl_files = [n for n in names if n.endswith(".mtl")]
                    for mtl_name in mtl_files:
                        mtl_data = zf.read(mtl_name)
                        mtl_out = obj_dir / os.path.basename(mtl_name)
                        with open(str(mtl_out), "wb") as f:
                            f.write(mtl_data)

                    tex_files = [n for n in names if "textures" in n and n.endswith(".png")]
                    for tex_name in tex_files:
                        tex_data = zf.read(tex_name)
                        tex_out = obj_dir / os.path.basename(tex_name)
                        with open(str(tex_out), "wb") as f:
                            f.write(tex_data)

                    if trimesh is not None:
                        try:
                            mesh = trimesh.load(str(obj_path), force="mesh", process=False)
                            if isinstance(mesh, trimesh.Scene):
                                meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
                                if meshes:
                                    mesh = meshes[0]
                            mesh.export(str(glb_path), file_type="glb")
                            converted = True
                            total_bytes += glb_path.stat().st_size
                            log_msg("    converted OBJ->GLB via trimesh (export glb)")
                        except Exception as conv_err:
                            log_msg("    WARNING: OBJ->GLB conversion failed: %s" % conv_err)
                            log_msg("    keeping OBJ as reference, no GLB output")

                elif dae_in_zip:
                    original_format = "dae"
                    mesh_source_path = dae_in_zip[0]
                    dae_data = zf.read(mesh_source_path)
                    dae_path = obj_dir / "model.dae"
                    with open(str(dae_path), "wb") as f:
                        f.write(dae_data)
                    if trimesh is not None:
                        try:
                            mesh = trimesh.load(str(dae_path), force="mesh", process=False)
                            mesh.export(str(glb_path), file_type="glb")
                            converted = True
                            total_bytes += glb_path.stat().st_size
                            log_msg("    converted DAE->GLB via trimesh")
                        except Exception as conv_err:
                            log_msg("    WARNING: DAE->GLB conversion failed: %s" % conv_err)

                if not mesh_source_path and not glb_path.exists():
                    log_msg("    WARNING: no mesh file found in ZIP")
                    record_exclusion(GSO_OWNER, oid, str(temp_zip), "mesh_missing")
                else:
                    meta = {
                        "source": "Google Scanned Objects (Gazebo Fuel)",
                        "object_id": oid,
                        "owner": GSO_OWNER,
                        "download_url": url,
                        "download_timestamp": now_str(),
                        "script_version": SCRIPT_VERSION,
                        "zip_contents": names,
                        "original_mesh_format": original_format,
                        "mesh_source_in_zip": mesh_source_path,
                        "converted_to_glb": converted,
                        "conversion_tool": "trimesh.export(file_type='glb')" if converted else None,
                        "zip_size_bytes": zip_size,
                    }
                    with open(str(meta_path), "w", encoding="utf-8") as f:
                        json.dump(meta, f, indent=2)

            temp_zip.unlink()
            succeeded += 1
            log_msg("  OK (%s, %d files in zip)" % (format_bytes(zip_size), len(names)))

        except zipfile.BadZipFile:
            log_msg("  FAILED: BadZipFile")
            record_exclusion(GSO_OWNER, oid, str(temp_zip), "invalid_zip")
            temp_zip.unlink()
            failed += 1
        except Exception as e:
            log_msg("  FAILED: %s" % e)
            record_exclusion(GSO_OWNER, oid, str(temp_zip), "download_failed")
            failed += 1

    log_msg("\nDownload summary:")
    log_msg("  Succeeded: %d" % succeeded)
    log_msg("  Failed:    %d" % failed)
    log_msg("  Skipped:   %d" % skipped)
    log_msg("  Total size: %s" % format_bytes(total_bytes))


_all_objects_cache = None


def load_all_objects_cached() -> list:
    global _all_objects_cache
    if _all_objects_cache is not None:
        return _all_objects_cache
    cache_path = MANIFEST_DIR / "gso_all_objects.json"
    if cache_path.exists():
        with open(str(cache_path), "r", encoding="utf-8") as f:
            _all_objects_cache = json.load(f)
    return _all_objects_cache or []


# ---------------------------------------------------------------------------
#   Mode: --validate
# ---------------------------------------------------------------------------

def validate_objects(selected_ids: list, args):
    if trimesh is None:
        log_msg("ERROR: trimesh required for --validate")
        return

    limit = args.limit or len(selected_ids)
    selected_ids = selected_ids[:limit]

    valid = 0
    invalid = 0
    no_glb = 0

    for idx, oid in enumerate(selected_ids):
        obj_dir = GSO_DIR / safe_obj_id(oid)
        glb_path = obj_dir / "model.glb"

        if not glb_path.exists():
            log_msg("  [%d/%d] %s: GLB not found" % (idx + 1, len(selected_ids), oid))
            no_glb += 1
            continue

        sz = glb_path.stat().st_size
        if sz == 0:
            log_msg("  [%d/%d] %s: empty file" % (idx + 1, len(selected_ids), oid))
            record_exclusion(GSO_OWNER, oid, str(glb_path), "empty_file")
            invalid += 1
            continue

        try:
            mesh = trimesh.load(str(glb_path), force="mesh", process=False)
            if isinstance(mesh, trimesh.Scene):
                meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
                if not meshes:
                    raise ValueError("no Trimesh geometry in scene")
                mesh = meshes[0]
            if len(mesh.vertices) < 10 or len(mesh.faces) < 5:
                log_msg("  [%d/%d] %s: mesh too small (%d verts, %d faces)" %
                        (idx + 1, len(selected_ids), oid, len(mesh.vertices), len(mesh.faces)))
                record_exclusion(GSO_OWNER, oid, str(glb_path), "mesh_missing")
                invalid += 1
                continue
            has_tex = (mesh.visual is not None and
                       hasattr(mesh.visual, "material") and
                       mesh.visual.material is not None and
                       hasattr(mesh.visual.material, "image") and
                       mesh.visual.material.image is not None)
            tex_warn = "" if has_tex else " [no texture]"
            log_msg("  [%d/%d] %s: OK (%d verts, %d faces)%s" %
                    (idx + 1, len(selected_ids), oid, len(mesh.vertices), len(mesh.faces), tex_warn))
            if not has_tex:
                record_exclusion(GSO_OWNER, oid, str(glb_path), "texture_warning")
            valid += 1
        except Exception as e:
            log_msg("  [%d/%d] %s: invalid GLB: %s" % (idx + 1, len(selected_ids), oid, e))
            record_exclusion(GSO_OWNER, oid, str(glb_path), "invalid_glb")
            invalid += 1

    log_msg("\nValidation summary:")
    log_msg("  Valid:   %d" % valid)
    log_msg("  Invalid: %d" % invalid)
    log_msg("  Missing: %d" % no_glb)
    return valid


# ---------------------------------------------------------------------------
#   Mode: --render
# ---------------------------------------------------------------------------

def render_objects(selected_ids: list, args):
    if trimesh is None:
        log_msg("ERROR: trimesh required for --render")
        return

    limit = args.limit or len(selected_ids)
    selected_ids = selected_ids[:limit]

    rendered = 0
    failed = 0
    skipped = 0

    for idx, oid in enumerate(selected_ids):
        obj_dir = GSO_DIR / safe_obj_id(oid)
        glb_path = obj_dir / "model.glb"
        render_dir = obj_dir / "renders"
        render_path = render_dir / "front.png"

        if render_path.exists() and render_path.stat().st_size > 0:
            log_msg("  [%d/%d] %s: render already exists, skipping" % (idx + 1, len(selected_ids), oid))
            skipped += 1
            rendered += 1
            continue

        if not glb_path.exists():
            log_msg("  [%d/%d] %s: GLB not found, skipping" % (idx + 1, len(selected_ids), oid))
            continue

        try:
            mesh = trimesh.load(str(glb_path), force="mesh", process=False)
            if isinstance(mesh, trimesh.Scene):
                meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
                if meshes:
                    mesh = meshes[0]
                else:
                    raise ValueError("no mesh in scene")

            mesh.apply_translation(-mesh.centroid)
            scale = np.abs(mesh.vertices).max()
            if scale > 0:
                mesh.apply_scale(1.0 / scale)

            scene = trimesh.Scene(mesh)

            camera_distance = CAMERA_DISTANCE_FACTOR
            camera_transform = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, camera_distance],
                [0, 0, 0, 1],
            ])
            scene.camera_transform = camera_transform
            scene.camera.resolution = (RENDER_SIZE, RENDER_SIZE)

            data = scene.save_image(resolution=(RENDER_SIZE, RENDER_SIZE), visible=True)
            img = Image.open(io.BytesIO(data)).convert("RGBA")

            os.makedirs(str(render_dir), exist_ok=True)
            img.save(str(render_path))

            meta_path = obj_dir / "metadata.json"
            if meta_path.exists():
                with open(str(meta_path), "r", encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                meta = {}
            meta["render"] = {
                "front_png": str(render_path),
                "resolution": [RENDER_SIZE, RENDER_SIZE],
                "camera_distance": camera_distance,
                "camera_transform": camera_transform.tolist(),
                "centered": True,
                "scaled_unit": True,
                "background": "transparent",
                "timestamp": now_str(),
            }
            with open(str(meta_path), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

            rendered += 1
            log_msg("  [%d/%d] %s: render OK (%s)" % (idx + 1, len(selected_ids), oid, format_bytes(render_path.stat().st_size)))

        except Exception as e:
            log_msg("  [%d/%d] %s: render FAILED: %s" % (idx + 1, len(selected_ids), oid, e))
            record_exclusion(GSO_OWNER, oid, str(glb_path), "render_failed")
            failed += 1

    log_msg("\nRender summary:")
    log_msg("  Rendered: %d" % rendered)
    log_msg("  Failed:   %d" % failed)
    log_msg("  Skipped:  %d" % skipped)


# ---------------------------------------------------------------------------
#   Manifest helpers
# ---------------------------------------------------------------------------

def record_exclusion(ds_source: str, obj_id: str, file_path: str, reason: str):
    os.makedirs(str(MANIFEST_DIR), exist_ok=True)
    exists = EXCLUDED_PATH.exists()
    with open(str(EXCLUDED_PATH), "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(EXCLUDED_HEADER)
        writer.writerow([ds_source, obj_id, file_path, reason, now_str(), SCRIPT_VERSION])


def write_manifest(objects_info: list):
    os.makedirs(str(MANIFEST_DIR), exist_ok=True)
    with open(str(MANIFEST_PATH), "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(MANIFEST_HEADER)
        for info in objects_info:
            writer.writerow([
                info.get("dataset_source", "GSO"),
                info.get("object_id", ""),
                info.get("class_name", ""),
                info.get("synset_id", ""),
                info.get("mesh_path", ""),
                info.get("image_path", ""),
                info.get("split", "test"),
                info.get("selection_reason", "deterministic_seed_42"),
                info.get("seed", ""),
                info.get("created_at", now_str()),
                info.get("script_version", SCRIPT_VERSION),
            ])
    log_msg("Manifest written: %s" % MANIFEST_PATH)


def update_summary():
    manifest_entries = 0
    if MANIFEST_PATH.exists():
        with open(str(MANIFEST_PATH), "r", encoding="utf-8-sig") as f:
            manifest_entries = sum(1 for _ in f) - 1

    total_glb = 0
    valid_glb = 0
    total_render = 0
    total_size = 0
    if GSO_DIR.exists():
        for od in GSO_DIR.iterdir():
            if od.is_dir():
                glb = od / "model.glb"
                front = od / "renders" / "front.png"
                if glb.exists():
                    total_glb += 1
                    total_size += glb.stat().st_size
                    try:
                        m = trimesh.load(str(glb), force="mesh", process=False)
                        if isinstance(m, trimesh.Scene):
                            m = [g for g in m.geometry.values() if isinstance(g, trimesh.Trimesh)]
                            if m:
                                m = m[0]
                            else:
                                continue
                        if len(m.vertices) >= 10:
                            valid_glb += 1
                    except Exception:
                        pass
                if front.exists():
                    total_render += 1

    summary_rows = []
    summary_rows.append(["GSO", "eval", "test", manifest_entries, total_render,
                          total_glb - valid_glb, 0, total_glb - total_render])
    with open(str(SUMMARY_PATH), "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "dataset_source", "class_name", "split", "object_count",
            "image_count", "missing_mesh_count", "missing_image_count",
            "render_failed_count",
        ])
        for row in summary_rows:
            writer.writerow(row)
    log_msg("Summary updated: %s" % SUMMARY_PATH)


# ---------------------------------------------------------------------------
#   Load selected IDs
# ---------------------------------------------------------------------------

def load_selected_ids() -> list:
    if SELECTED_IDS_PATH.exists():
        with open(str(SELECTED_IDS_PATH), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return [r["object_id"] for r in reader]
    return []


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Download, validate and render Google Scanned Objects for TripoSR evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --help
  %(prog)s --dry-run
  %(prog)s --list
  %(prog)s --select --count 300 --seed 42
  %(prog)s --download --limit 3
  %(prog)s --validate
  %(prog)s --render --limit 3
  %(prog)s --all --confirm-download
""")
    parser.add_argument("--list", action="store_true", help="List available object IDs")
    parser.add_argument("--select", action="store_true", help="Select object IDs deterministically")
    parser.add_argument("--count", type=int, default=300, help="Number of objects to select (default: 300)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for selection (default: 42)")
    parser.add_argument("--download", action="store_true", help="Download selected object zips")
    parser.add_argument("--validate", action="store_true", help="Check GLB integrity")
    parser.add_argument("--render", action="store_true", help="Render front views")
    parser.add_argument("--all", action="store_true", help="Run full pipeline (requires --confirm-download)")
    parser.add_argument("--confirm-download", action="store_true", help="Confirm to actually download data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--limit", type=int, default=None, help="Limit processing to N objects")
    parser.add_argument("--base-dir", type=str, default=None, help="Override project root directory")
    parser.add_argument("--reset-manifest", action="store_true", help="Reset gso_manifest.csv before adding")
    parser.add_argument("--selected-ids", type=str, default=None, help="Path to CSV with object IDs")

    args = parser.parse_args()

    if args.base_dir:
        global PROJECT_ROOT, GSO_DIR, MANIFEST_DIR, LOG_DIR, MANIFEST_PATH, EXCLUDED_PATH, SUMMARY_PATH, SELECTED_IDS_PATH
        PROJECT_ROOT = Path(args.base_dir)
        GSO_DIR = PROJECT_ROOT / "static" / "templates" / "gso"
        MANIFEST_DIR = PROJECT_ROOT / "experiments" / "data" / "manifests"
        LOG_DIR = PROJECT_ROOT / "experiments" / "logs"
        MANIFEST_PATH = MANIFEST_DIR / "gso_manifest.csv"
        EXCLUDED_PATH = MANIFEST_DIR / "excluded_samples.csv"
        SUMMARY_PATH = MANIFEST_DIR / "dataset_summary.csv"
        SELECTED_IDS_PATH = MANIFEST_DIR / "gso_selected_ids.csv"

    os.makedirs(str(LOG_DIR), exist_ok=True)
    os.makedirs(str(MANIFEST_DIR), exist_ok=True)

    if args.dry_run:
        log_msg("DRY RUN — no data will be downloaded or written")

    if args.reset_manifest:
        if not args.dry_run:
            with open(str(MANIFEST_PATH), "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow(MANIFEST_HEADER)
            log_msg("Manifest reset: %s" % MANIFEST_PATH)

    modes = [args.list, args.select, args.download, args.validate, args.render, args.all]
    active_modes = sum(1 for m in modes if m)

    if active_modes == 0:
        parser.print_help()
        print("\nNo mode selected. Use one or more of: --list, --select, --download, --validate, --render, --all")
        return

    if args.all:
        if not args.confirm_download:
            log_msg("ERROR: --all requires --confirm-download to proceed")
            return
        args.list = True
        args.select = True
        args.download = True
        args.validate = True
        args.render = True

    if args.download and not args.confirm_download and not args.all:
        log_msg("ERROR: --download requires --confirm-download (or use --all --confirm-download)")
        return

    objects = []
    selected_ids = []

    if args.list:
        log_msg("=== --list ===")
        objects = list_objects(args)
        if args.dry_run:
            return

    if args.select:
        log_msg("=== --select ===")
        if not objects:
            objects = load_all_objects_cached()
        if not objects:
            log_msg("No object list available. Run --list first.")
            return
        if args.dry_run:
            log_msg("Would select %d objects (seed=%d)" % (args.count, args.seed))
        else:
            selected_ids = select_objects(objects, args)

    if args.download:
        log_msg("=== --download ===")
        if not selected_ids:
            selected_ids = load_selected_ids()
        if not selected_ids:
            log_msg("No selected IDs. Run --select first or provide --selected-ids")
            return
        if args.dry_run:
            log_msg("Would download %d objects to %s" % (len(selected_ids), GSO_DIR))
        else:
            download_objects(selected_ids, args)

    if args.validate:
        log_msg("=== --validate ===")
        if not selected_ids:
            selected_ids = load_selected_ids()
        if not selected_ids:
            log_msg("No selected IDs found.")
            return
        if args.dry_run:
            log_msg("Would validate %d objects" % len(selected_ids))
        else:
            validate_objects(selected_ids, args)

    if args.render:
        log_msg("=== --render ===")
        if not selected_ids:
            selected_ids = load_selected_ids()
        if not selected_ids:
            log_msg("No selected IDs found.")
            return
        if args.dry_run:
            log_msg("Would render %d objects" % len(selected_ids))
        else:
            render_objects(selected_ids, args)

    if not args.dry_run and (args.render or args.validate or args.download):
        build_manifest_from_disk(selected_ids, args)

        update_summary()

    log_msg("Done.")
    print()
    print("=" * 60)
    print("GSO Preparation Summary")
    print("=" * 60)
    print("  GSO directory: %s" % GSO_DIR)
    if GSO_DIR.exists():
        total = sum(1 for _ in GSO_DIR.iterdir())
        print("  Object subdirs: %d" % total)
    print("  Manifest: %s" % MANIFEST_PATH)
    if MANIFEST_PATH.exists():
        with open(str(MANIFEST_PATH), "r", encoding="utf-8-sig") as f:
            print("  Manifest entries: %d" % (sum(1 for _ in f) - 1))
    print("  Log: %s" % (LOG_DIR / "gso_prepare.log"))
    if not args.dry_run:
        print("  Excluded: %s" % EXCLUDED_PATH)
    print("=" * 60)


def build_manifest_from_disk(selected_ids: list, args):
    if not selected_ids:
        return

    manifest_entries = []
    for oid in selected_ids:
        obj_dir = GSO_DIR / safe_obj_id(oid)

        ref_candidates = [
            ("model.obj", "obj"),
            ("model.glb", "glb"),
            ("model.dae", "dae"),
        ]
        mesh_path = None
        ref_format = None
        for fname, fmt in ref_candidates:
            candidate = obj_dir / fname
            if candidate.exists() and candidate.stat().st_size > 0:
                mesh_path = candidate
                ref_format = fmt
                break

        if not mesh_path:
            log_msg("  SKIP manifest %s: no reference mesh found" % oid)
            continue

        try:
            mesh = trimesh.load(str(mesh_path), force="mesh", process=False)
            if isinstance(mesh, trimesh.Scene):
                meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
                if not meshes:
                    log_msg("  SKIP manifest %s: no Trimesh in scene" % oid)
                    continue
            elif not isinstance(mesh, trimesh.Trimesh):
                log_msg("  SKIP manifest %s: not a Trimesh" % oid)
                continue
            if len(mesh.vertices) < 10:
                log_msg("  SKIP manifest %s: too few vertices (%d)" % (oid, len(mesh.vertices)))
                continue
        except Exception as e:
            log_msg("  SKIP manifest %s: mesh load failed: %s" % (oid, e))
            continue

        render_path = obj_dir / "renders" / "front.png"
        if not (render_path.exists() and render_path.stat().st_size > 0):
            log_msg("  SKIP manifest %s: render missing" % oid)
            continue

        rel_mesh = os.path.relpath(str(mesh_path), str(PROJECT_ROOT)).replace("\\", "/")
        rel_render = os.path.relpath(str(render_path), str(PROJECT_ROOT)).replace("\\", "/")

        manifest_entries.append({
            "dataset_source": "GSO",
            "object_id": oid,
            "class_name": "",
            "synset_id": "",
            "mesh_path": rel_mesh,
            "image_path": rel_render,
            "split": "test",
            "selection_reason": "deterministic_seed_42",
            "seed": str(args.seed if hasattr(args, 'seed') and args.seed else 42),
            "created_at": now_str(),
            "script_version": SCRIPT_VERSION,
        })

    if manifest_entries:
        write_manifest(manifest_entries)
        log_msg("Manifest: %d entries written" % len(manifest_entries))
    else:
        log_msg("No valid objects to add to manifest")


if __name__ == "__main__":
    main()
