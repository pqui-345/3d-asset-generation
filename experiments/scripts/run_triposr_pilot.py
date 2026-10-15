#!/usr/bin/env python3
"""
run_triposr_pilot.py — G7 Pilot: Batch TripoSR inference on 10 GSO objects.

Usage:
  python experiments/scripts/run_triposr_pilot.py
  python experiments/scripts/run_triposr_pilot.py --resume  (retry failed only)
"""

import os, sys, csv, json, time
from pathlib import Path
from datetime import datetime, timezone
from collections import OrderedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import torch
import numpy as np
from PIL import Image

from services.local_tripo_service import LocalTripoService

SCRIPT_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GSO_DIR = PROJECT_ROOT / "static" / "templates" / "gso"
OUTPUT_DIR = PROJECT_ROOT / "experiments" / "outputs" / "predictions" / "triposr_pilot"
MANIFEST_DIR = PROJECT_ROOT / "experiments" / "data" / "manifests"
LOG_DIR = PROJECT_ROOT / "experiments" / "logs"
EXCLUDED_PATH = MANIFEST_DIR / "excluded_samples.csv"

EXCLUDED_HEADER = ["dataset_source", "object_id", "file_path", "exclusion_reason", "created_at", "script_version"]

# 10 diverse GSO objects
SELECTED = [
    "BAGEL_WITH_CHEESE",
    "Dog",
    "Racoon",
    "Razer_BlackWidow_Ultimate_2014_Mechanical_Gaming_Keyboard",
    "Hefty_Waste_Basket_Decorative_Bronze_85_liter",
    "Connect_4_Launchers",
    "Timberland_Womens_Earthkeepers_Classic_Unlined_Boat_Shoe",
    "Cole_Hardware_School_Bell_Solid_Brass_38",
    "Down_To_Earth_Orchid_Pot_Ceramic_Lime",
    "LEGO_Star_Wars_Advent_Calendar",
]


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))


def record_exclusion(oid, reason, file_path=""):
    os.makedirs(str(MANIFEST_DIR), exist_ok=True)
    exists = EXCLUDED_PATH.exists()
    with open(str(EXCLUDED_PATH), "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(EXCLUDED_HEADER)
        w.writerow(["GSO", oid, file_path, reason, now_str(), SCRIPT_VERSION])


def check_render_quality(img_path):
    """Basic visual sanity: no all-white, no all-black, no silhouette."""
    try:
        img = Image.open(str(img_path)).convert("RGBA")
        arr = np.array(img)
        rgb = arr[:, :, :3]
        h, w = arr.shape[:2]

        # Non-background pixels (not near-white)
        obj_mask = rgb.min(axis=2) <= 250
        obj_pct = obj_mask.mean() * 100

        if obj_pct < 5:
            return ("FAIL", "Object covers only %.1f%% of frame" % obj_pct)

        obj_rgb = rgb[obj_mask]
        if len(obj_rgb) == 0:
            return ("FAIL", "No object pixels found")

        # Check object not all-white or all-black
        white_obj = (obj_rgb.min(axis=1) > 250).mean() * 100
        black_obj = (obj_rgb.max(axis=1) < 5).mean() * 100
        if white_obj > 80:
            return ("FAIL", "Object is %.0f%% white" % white_obj)
        if black_obj > 80:
            return ("FAIL", "Object is %.0f%% black" % black_obj)

        # Color variation check
        uniq = len(np.unique(obj_rgb[np.random.choice(len(obj_rgb), min(2000, len(obj_rgb)), replace=False)].astype(np.uint8), axis=0))
        if uniq < 10:
            return ("FAIL", "Only %d unique colors (silhouette)" % uniq)

        # Check centering
        cx, cy = w // 2, h // 2
        center = obj_mask[cy-20:cy+20, cx-20:cx+20]
        if center.mean() < 0.3:
            return ("WARN", "Object not centered (center coverage %.0f%%)" % (center.mean()*100))

        return ("PASS", "OK (%.0f%% coverage, %d colors)" % (obj_pct, uniq))
    except Exception as e:
        return ("FAIL", str(e))


def generate_preview(glb_path, output_png):
    """Render a quick preview of the output GLB."""
    try:
        import trimesh
        mesh = trimesh.load(str(glb_path), force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if meshes:
                mesh = meshes[0]
            else:
                return False
        mesh.apply_translation(-mesh.centroid)
        scale = np.abs(mesh.vertices).max()
        if scale > 0:
            mesh.apply_scale(1.0 / scale)
        scene = trimesh.Scene(mesh)
        import io
        data = scene.save_image(resolution=(256, 256), visible=True)
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img.save(str(output_png))
        return True
    except Exception:
        return False


def main():
    os.makedirs(str(OUTPUT_DIR), exist_ok=True)
    os.makedirs(str(LOG_DIR), exist_ok=True)
    log_path = LOG_DIR / "triposr_pilot.csv"
    results = []

    # Resume check
    resume = "--resume" in sys.argv
    completed_ids = set()
    if resume and log_path.exists():
        with open(str(log_path), "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("status") == "success":
                    completed_ids.add(r["object_id"])
        log("Resume mode: %d already completed" % len(completed_ids))

    # Init TripoSR
    log("Initializing TripoSR ...")
    t0 = time.time()
    tripo = LocalTripoService()
    tripo._load_model()
    log("Model loaded in %.1f s" % (time.time() - t0))

    for idx, oid in enumerate(SELECTED):
        log("[%d/%d] %s ..." % (idx + 1, len(SELECTED), oid))

        if oid in completed_ids:
            log("  SKIP (already completed)")
            continue

        render_path = GSO_DIR / oid / "renders" / "front.png"
        sample_dir = OUTPUT_DIR / oid
        sample_dir.mkdir(parents=True, exist_ok=True)

        if not render_path.exists():
            log("  FAIL: render not found")
            record_exclusion(oid, "render_not_found", str(render_path))
            results.append({"object_id": oid, "status": "failed", "error": "render_not_found"})
            continue

        # Visual check on input
        status, msg = check_render_quality(render_path)
        if status == "FAIL":
            log("  FAIL: input quality check: %s" % msg)
            record_exclusion(oid, "input_quality_fail", str(render_path))
            results.append({"object_id": oid, "status": "failed", "error": msg})
            continue

        # rembg preprocessing (via TripoSR's own pipeline)
        try:
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.empty_cache()
            vram_before = torch.cuda.memory_allocated() / 1e6

            t1 = time.time()
            result = tripo.generate_3d(
                image_paths=[str(render_path)],
                output_dir=str(sample_dir),
                asset_name=oid,
            )
            elapsed = time.time() - t1
            vram_peak = torch.cuda.max_memory_allocated() / 1e6
            vram_after = torch.cuda.memory_allocated() / 1e6
        except Exception as e:
            log("  FAIL: inference crashed: %s" % e)
            record_exclusion(oid, "inference_failed", str(sample_dir))
            results.append({"object_id": oid, "status": "failed", "error": str(e)})
            continue

        glb_path = sample_dir / ("%s.glb" % oid)
        obj_path = sample_dir / ("%s.obj" % oid)
        glb_sz = glb_path.stat().st_size if glb_path.exists() else 0
        obj_sz = obj_path.stat().st_size if obj_path.exists() else 0
        verts = result.get("vertices", 0)
        faces = result.get("faces", 0)

        # Generate preview
        preview_path = sample_dir / "preview.png"
        preview_ok = generate_preview(glb_path, preview_path)

        # Check input quality
        qual_status, qual_msg = check_render_quality(render_path)

        entry = OrderedDict([
            ("object_id", oid),
            ("status", "success"),
            ("inference_time_s", round(elapsed, 1)),
            ("vram_before_mb", round(vram_before, 0)),
            ("vram_peak_mb", round(vram_peak, 0)),
            ("vram_after_mb", round(vram_after, 0)),
            ("vertices", verts),
            ("faces", faces),
            ("glb_size_mb", round(glb_sz / 1e6, 2)),
            ("obj_size_mb", round(obj_sz / 1e6, 2)),
            ("preview_ok", preview_ok),
            ("input_quality", qual_status),
            ("error", ""),
        ])
        results.append(entry)

        log("  Time: %.1f s, VRAM: %.0f MB peak, Mesh: %d verts/%d faces, GLB: %.2f MB"
            % (elapsed, vram_peak, verts, faces, glb_sz / 1e6))
        log("  Input quality: %s — %s" % (qual_status, qual_msg))
        log("  Preview: %s" % ("OK" if preview_ok else "FAILED"))

        # Save incremental log
        with open(str(log_path), "w", newline="", encoding="utf-8-sig") as f:
            if results:
                w = csv.DictWriter(f, fieldnames=results[0].keys())
                w.writeheader()
                w.writerows(results)

    # Summary
    print()
    print("=" * 90)
    print("PILOT SUMMARY — 10 GSO objects")
    print("=" * 90)

    success = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "failed"]

    if success:
        times = [r["inference_time_s"] for r in success]
        vrams = [r["vram_peak_mb"] for r in success]
        verts_list = [r["vertices"] for r in success]
        faces_list = [r["faces"] for r in success]
        glbs = [r["glb_size_mb"] for r in success]
        objs = [r["obj_size_mb"] for r in success]

        print()
        print("%-55s %8s %8s %8s %8s %8s" % ("Object", "Time(s)", "VRAM(MB)", "Verts", "Faces", "GLB(MB)"))
        print("-" * 95)
        for r in success:
            print("%-55s %8.1f %8.0f %8d %8d %8.2f" % (
                r["object_id"][:53], r["inference_time_s"], r["vram_peak_mb"],
                r["vertices"], r["faces"], r["glb_size_mb"]))
        print("-" * 95)
        print("%-55s %8.1f %8.0f %8d %8d %8.2f" % (
            "AVERAGE", np.mean(times), np.mean(vrams),
            int(np.mean(verts_list)), int(np.mean(faces_list)), np.mean(glbs)))
        print()
        print("  Total succeeded: %d / %d" % (len(success), len(results)))
        print("  Failed:          %d" % len(failed))
        print("  Avg time:        %.1f s" % np.mean(times))
        print("  Avg VRAM peak:   %.0f MB" % np.mean(vrams))
        print("  Avg verts:       %d" % int(np.mean(verts_list)))
        print("  Avg faces:       %d" % int(np.mean(faces_list)))
        print("  Avg GLB size:    %.2f MB" % np.mean(glbs))

        # Full metrics JSON
        metrics = {
            "experiment": "triposr_pilot",
            "script_version": SCRIPT_VERSION,
            "timestamp": now_str(),
            "n_selected": len(SELECTED),
            "n_succeeded": len(success),
            "n_failed": len(failed),
            "avg_inference_time_s": round(float(np.mean(times)), 1),
            "std_inference_time_s": round(float(np.std(times)), 1),
            "avg_vram_peak_mb": round(float(np.mean(vrams)), 0),
            "max_vram_peak_mb": round(float(max(vrams)), 0),
            "avg_vertices": int(np.mean(verts_list)),
            "avg_faces": int(np.mean(faces_list)),
            "avg_glb_size_mb": round(float(np.mean(glbs)), 2),
        }
        metrics_path = LOG_DIR / "triposr_pilot_metrics.json"
        with open(str(metrics_path), "w") as f:
            json.dump(metrics, f, indent=2)
        print("  Metrics saved:   %s" % metrics_path)
    else:
        print("  No successful runs")

    if failed:
        print()
        print("Failed samples:")
        for r in failed:
            print("  - %s: %s" % (r["object_id"], r.get("error", "unknown")))

    print()
    print("=" * 90)
    print("Output: %s" % OUTPUT_DIR)
    print("Log:    %s" % log_path)
    print("=" * 90)


if __name__ == "__main__":
    main()
