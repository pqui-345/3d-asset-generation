#!/usr/bin/env python3
"""
download_shapenet.py — G2: Download ShapeNetCore v2 subset (5 classes) from HuggingFace.

Usage:
  python experiments/scripts/download_shapenet.py --help
  python experiments/scripts/download_shapenet.py --list
  python experiments/scripts/download_shapenet.py --download          # prompts for HF token
  python experiments/scripts/download_shapenet.py --download --token hf_xxxx
  python experiments/scripts/download_shapenet.py --validate
  python experiments/scripts/download_shapenet.py --all --token hf_xxxx
  python experiments/scripts/download_shapenet.py --manifest-only     # rebuild manifest from existing files
"""

import os, sys, csv, json, time, zipfile, io, re, argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

SCRIPT_VERSION = "1.0.0"
SCRIPT_NAME = "download_shapenet.py"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = PROJECT_ROOT / "experiments" / "data" / "manifests"
SHAPENET_DIR = PROJECT_ROOT / "experiments" / "data" / "ShapeNetCore.v2"
LOG_DIR = PROJECT_ROOT / "experiments" / "logs"

MANIFEST_PATH = MANIFEST_DIR / "dataset_manifest_shapenet.csv"
SUMMARY_PATH = MANIFEST_DIR / "dataset_summary.csv"

HF_BASE = "https://huggingface.co/datasets/ShapeNet/ShapeNetCore/resolve/main"

SYNSETS = {
    "03001627": "chair",
    "04379243": "table",
    "03636649": "lamp",
    "02876657": "bottle",
    "03797390": "mug",
}

DOWNLOAD_TIMEOUT = 600
DOWNLOAD_RETRIES = 3

MANIFEST_HEADER = [
    "dataset_source", "object_id", "class_name", "synset_id",
    "mesh_path", "image_path", "split", "selection_reason",
    "seed", "created_at", "script_version",
]


def log_msg(msg: str):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_bytes(n: int) -> str:
    if n < 1024: return "%d B" % n
    elif n < 1024 ** 2: return "%.1f KB" % (n / 1024)
    else: return "%.1f MB" % (n / (1024 ** 2))


# ---------------------------------------------------------------------------
#   Mode: --list / info
# ---------------------------------------------------------------------------

def print_info():
    print("=" * 60)
    print("ShapeNetCore v2 — Subset Info")
    print("=" * 60)
    print("Source: https://huggingface.co/datasets/ShapeNet/ShapeNetCore")
    print("License: Non-commercial research (ShapeNet terms)")
    print("Access: Gated — requires HF account + approval")
    print()
    print("Target classes (%d):" % len(SYNSETS))
    total_est = 0
    for sid, cname in SYNSETS.items():
        dest = SHAPENET_DIR / sid
        existing = count_models(dest)
        status = "%d models" % existing if existing > 0 else "NOT_DOWNLOADED"
        print("  %s  %-10s  %s" % (sid, cname, status))
        total_est += 1
    print()
    print("Expected path: %s/{synset_id}/{model_id}/models/model_normalized.obj" % SHAPENET_DIR)
    print()
    print("Manifest: %s" % MANIFEST_PATH)
    if MANIFEST_PATH.exists():
        with open(str(MANIFEST_PATH)) as f:
            n = sum(1 for _ in f) - 1
        print("  entries: %d" % max(0, n))
    print("=" * 60)


def count_models(synset_dir: Path) -> int:
    if not synset_dir.exists():
        return 0
    count = 0
    for child in synset_dir.iterdir():
        if child.is_dir():
            obj = child / "models" / "model_normalized.obj"
            if obj.exists():
                count += 1
    return count


# ---------------------------------------------------------------------------
#   Mode: --download
# ---------------------------------------------------------------------------

def download_shapenet(token: str):
    if requests is None:
        log_msg("ERROR: 'requests' library required for download")
        sys.exit(1)

    if not token:
        log_msg("ERROR: HF token required. Use --token or set HF_TOKEN env var")
        sys.exit(1)

    headers = {
        "Authorization": "Bearer %s" % token,
        "User-Agent": "Mozilla/5.0",
    }

    # Test token
    try:
        r = requests.get("https://huggingface.co/api/whoami-v2", headers=headers, timeout=10)
        if r.status_code == 200:
            user = r.json().get("name", r.json().get("user"))
            log_msg("Authenticated as: %s" % user)
        else:
            log_msg("WARNING: Token validation returned %d (may still work)" % r.status_code)
    except Exception:
        log_msg("WARNING: Could not validate token (will attempt download anyway)")

    os.makedirs(str(SHAPENET_DIR), exist_ok=True)
    total_succeeded = 0
    total_failed = 0
    total_skipped = 0
    total_bytes = 0

    for synset_id, class_name in SYNSETS.items():
        dest_dir = SHAPENET_DIR / synset_id
        marker = dest_dir / ".download_complete"

        if marker.exists():
            models = count_models(dest_dir)
            log_msg("  %s (%s): already downloaded (%d models), skipping" % (synset_id, class_name, models))
            total_skipped += 1
            continue

        zip_url = "%s/%s.zip" % (HF_BASE, synset_id)
        zip_path = dest_dir / ("%s.zip" % synset_id)
        temp_zip = dest_dir / ".download.part"

        log_msg("  [%s/%s] %s %s: downloading ..." % (
            list(SYNSETS.keys()).index(synset_id) + 1, len(SYNSETS), synset_id, class_name))

        os.makedirs(str(dest_dir), exist_ok=True)

        success = False
        for attempt in range(DOWNLOAD_RETRIES):
            try:
                r = requests.get(zip_url, headers=headers, timeout=DOWNLOAD_TIMEOUT, stream=True)
                if r.status_code == 401 or r.status_code == 403:
                    log_msg("    ERROR: Access denied (HTTP %d). Make sure you have access to ShapeNet/ShapeNetCore on HF" % r.status_code)
                    log_msg("    Visit: https://huggingface.co/datasets/ShapeNet/ShapeNetCore")
                    sys.exit(1)
                if r.status_code == 404:
                    log_msg("    ERROR: %s.zip not found (HTTP 404)" % synset_id)
                    break
                if r.status_code != 200:
                    log_msg("    attempt %d: HTTP %d" % (attempt + 1, r.status_code))
                    time.sleep(5)
                    continue

                total = int(r.headers.get("content-length", 0))
                downloaded = 0
                with open(str(temp_zip), "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                pct = downloaded * 100 // total
                                if pct % 25 == 0 and downloaded > 0:
                                    log_msg("    ... %d%% (%s / %s)" % (pct, format_bytes(downloaded), format_bytes(total)))

                if temp_zip.stat().st_size < 1000:
                    log_msg("    FAILED: file too small (%d bytes)" % temp_zip.stat().st_size)
                    temp_zip.unlink()
                    success = False
                    break

                success = True
                break
            except requests.exceptions.ConnectionError as e:
                log_msg("    attempt %d connection error: %s" % (attempt + 1, e))
                time.sleep(10)
            except Exception as e:
                log_msg("    attempt %d failed: %s" % (attempt + 1, e))
                time.sleep(5)

        if not success:
            log_msg("  FAILED: download exhausted")
            if temp_zip.exists():
                temp_zip.unlink()
            total_failed += 1
            continue

        zip_size = temp_zip.stat().st_size
        total_bytes += zip_size

        # Extract
        try:
            extract_count = 0
            with zipfile.ZipFile(str(temp_zip), "r") as zf:
                names = zf.namelist()
                log_msg("    Extracting %d files from zip ..." % len(names))
                for name in names:
                    # Zip contains entries like: 03001627/abcd1234/models/model_normalized.obj
                    # We want to strip the top-level synset dir to extract directly
                    parts = name.split("/", 1)
                    if len(parts) > 1:
                        rel_path = parts[1]
                    else:
                        rel_path = name
                    if rel_path == "":
                        continue
                    out_path = dest_dir / rel_path
                    if name.endswith("/"):
                        os.makedirs(str(out_path), exist_ok=True)
                    else:
                        os.makedirs(str(out_path.parent), exist_ok=True)
                        with zf.open(name) as src, open(str(out_path), "wb") as dst:
                            dst.write(src.read())
                            if rel_path.endswith("model_normalized.obj"):
                                extract_count += 1

            temp_zip.unlink()
            total_succeeded += 1
            log_msg("    OK (%s, %d OBJ models)" % (format_bytes(zip_size), extract_count))

            # Write completion marker
            with open(str(marker), "w") as f:
                f.write("download_complete\nsynset_id=%s\nclass=%s\ntimestamp=%s\nzip_size_bytes=%s\nmodels=%d\nscript_version=%s\n" % (
                    synset_id, class_name, now_str(), zip_size, extract_count, SCRIPT_VERSION))

        except Exception as e:
            log_msg("    FAILED extracting: %s" % e)
            if temp_zip.exists():
                temp_zip.unlink()
            total_failed += 1

    log_msg("\nDownload summary:")
    log_msg("  Succeeded: %d" % total_succeeded)
    log_msg("  Failed:    %d" % total_failed)
    log_msg("  Skipped:   %d" % total_skipped)
    log_msg("  Total zip: %s" % format_bytes(total_bytes))


# ---------------------------------------------------------------------------
#   Mode: --validate
# ---------------------------------------------------------------------------

def validate_shapenet():
    log_msg("=== --validate ===")
    valid = 0
    invalid = 0

    for synset_id, class_name in SYNSETS.items():
        synset_dir = SHAPENET_DIR / synset_id
        if not synset_dir.exists():
            log_msg("  %s (%s): NOT FOUND" % (synset_id, class_name))
            continue

        model_ids = sorted([d.name for d in synset_dir.iterdir() if d.is_dir()])
        synset_valid = 0
        synset_invalid = 0

        for mid in model_ids:
            obj_path = synset_dir / mid / "models" / "model_normalized.obj"
            if not obj_path.exists():
                synset_invalid += 1
                continue
            sz = obj_path.stat().st_size
            if sz < 100:
                synset_invalid += 1
                continue
            synset_valid += 1

        valid += synset_valid
        invalid += synset_invalid
        log_msg("  %s (%s): %d valid, %d invalid (of %d total dirs)" %
                (synset_id, class_name, synset_valid, synset_invalid, len(model_ids)))

    log_msg("\nValidate summary: %d valid, %d invalid" % (valid, invalid))
    return valid


# ---------------------------------------------------------------------------
#   Manifest
# ---------------------------------------------------------------------------

def build_manifest():
    log_msg("Building manifest ...")
    entries = []

    for synset_id, class_name in SYNSETS.items():
        synset_dir = SHAPENET_DIR / synset_id
        if not synset_dir.exists():
            log_msg("  SKIP %s: directory not found" % synset_id)
            continue

        model_ids = sorted([d.name for d in synset_dir.iterdir() if d.is_dir()])
        for mid in model_ids:
            obj_path = synset_dir / mid / "models" / "model_normalized.obj"
            if not obj_path.exists():
                continue

            rel_mesh = os.path.relpath(str(obj_path), str(PROJECT_ROOT)).replace("\\", "/")

            entries.append({
                "dataset_source": "ShapeNetCore.v2",
                "object_id": mid,
                "class_name": class_name,
                "synset_id": synset_id,
                "mesh_path": rel_mesh,
                "image_path": "",  # no render for ShapeNet (yet)
                "split": "train",  # default, can be adjusted
                "selection_reason": "synset_%s" % synset_id,
                "seed": "",
                "created_at": now_str(),
                "script_version": SCRIPT_VERSION,
            })

    os.makedirs(str(MANIFEST_DIR), exist_ok=True)
    with open(str(MANIFEST_PATH), "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(MANIFEST_HEADER)
        for e in entries:
            writer.writerow([
                e["dataset_source"], e["object_id"], e["class_name"], e["synset_id"],
                e["mesh_path"], e["image_path"], e["split"], e["selection_reason"],
                e["seed"], e["created_at"], e["script_version"],
            ])

    log_msg("Manifest written: %s (%d entries)" % (MANIFEST_PATH, len(entries)))
    return entries


def update_summary():
    shapenet_count = 0
    for synset_id in SYNSETS:
        shapenet_count += count_models(SHAPENET_DIR / synset_id)

    os.makedirs(str(MANIFEST_DIR), exist_ok=True)
    with open(str(SUMMARY_PATH), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["dataset_source", "class_name", "split", "object_count",
                     "image_count", "missing_mesh_count", "missing_image_count",
                     "render_failed_count"])
        w.writerow(["ShapeNetCore.v2", "", "all", shapenet_count, 0, 0, 0, 0])
    log_msg("Summary updated: %s" % SUMMARY_PATH)


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Download ShapeNetCore v2 (5 classes) from HuggingFace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --help
  %(prog)s --list
  %(prog)s --download --token hf_xxxx
  %(prog)s --validate
  %(prog)s --manifest-only
  %(prog)s --all --token hf_xxxx
        """)
    parser.add_argument("--list", action="store_true", help="Show dataset info and download status")
    parser.add_argument("--download", action="store_true", help="Download ShapeNet subset from HF")
    parser.add_argument("--validate", action="store_true", help="Validate downloaded OBJ files")
    parser.add_argument("--manifest-only", action="store_true", help="Rebuild manifest from existing files (no download)")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: download + validate + manifest")
    parser.add_argument("--token", type=str, default=None, help="HuggingFace access token")
    parser.add_argument("--base-dir", type=str, default=None, help="Override project root")
    parser.add_argument("--reset-manifest", action="store_true", help="Clear manifest before writing")

    args = parser.parse_args()

    if args.base_dir:
        global PROJECT_ROOT, SHAPENET_DIR, MANIFEST_DIR, MANIFEST_PATH, SUMMARY_PATH
        PROJECT_ROOT = Path(args.base_dir)
        SHAPENET_DIR = PROJECT_ROOT / "experiments" / "data" / "ShapeNetCore.v2"
        MANIFEST_DIR = PROJECT_ROOT / "experiments" / "data" / "manifests"
        MANIFEST_PATH = MANIFEST_DIR / "dataset_manifest_shapenet.csv"
        SUMMARY_PATH = MANIFEST_DIR / "dataset_summary.csv"

    os.makedirs(str(LOG_DIR), exist_ok=True)
    os.makedirs(str(MANIFEST_DIR), exist_ok=True)

    if args.reset_manifest:
        os.makedirs(str(MANIFEST_DIR), exist_ok=True)
        with open(str(MANIFEST_PATH), "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(MANIFEST_HEADER)
        log_msg("Manifest reset: %s" % MANIFEST_PATH)

    if args.list or args.all:
        print_info()
        if not args.all:
            return

    if args.all:
        args.download = True
        args.validate = True

    if args.download:
        log_msg("=== --download ===")
        token = args.token or os.environ.get("HF_TOKEN", "")
        download_shapenet(token)

    if args.validate:
        log_msg("=== --validate ===")
        validate_shapenet()

    if args.download or args.validate or args.manifest_only:
        log_msg("=== manifest ===")
        build_manifest()
        update_summary()

    print()
    print("=" * 60)
    print("ShapeNetCore Preparation Summary")
    print("=" * 60)
    print("  ShapeNet dir: %s" % SHAPENET_DIR)
    for sid, cn in SYNSETS.items():
        n = count_models(SHAPENET_DIR / sid)
        print("    %s  %-10s  %d models" % (sid, cn, n))
    print("  Manifest: %s" % MANIFEST_PATH)
    print("=" * 60)
    log_msg("Done.")


if __name__ == "__main__":
    main()
