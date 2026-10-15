#!/usr/bin/env python3
"""
run_gso_experiment_30.py — Run TripoSR on 30 GSO samples + ICP-aligned geometry metrics.
"""
import os, sys, json, csv, time, io
from pathlib import Path
from datetime import datetime, timezone
from collections import OrderedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import torch
import numpy as np
from PIL import Image
import trimesh
from scipy.spatial import KDTree

from services.local_tripo_service import LocalTripoService

SCRIPT_VERSION = "2.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GSO_DIR = PROJECT_ROOT / "static" / "templates" / "gso"
OUTPUT_DIR = PROJECT_ROOT / "experiments" / "outputs" / "predictions" / "triposr_30"
PILOT_OUTPUT_DIR = PROJECT_ROOT / "experiments" / "outputs" / "predictions" / "triposr_pilot"
LOG_DIR = PROJECT_ROOT / "experiments" / "logs"
METRICS_DIR = PROJECT_ROOT / "experiments" / "outputs" / "metrics"
COMPARISON_DIR = PROJECT_ROOT / "BaoCao_TotNghiep" / "report_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(COMPARISON_DIR, exist_ok=True)

# 10 existing pilot + 20 new = 30 total
EXISTING_10 = [
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

SELECTED_20 = [
    "ASICS_GEL1140V_WhiteRoyalSilver",
    "BABY_CAR",
    "BEDROOM_CLASSIC",
    "Black_Decker_CM2035B_12Cup_Thermal_Coffeemaker",
    "BlueBlack_Nintendo_3DSXL",
    "Crayola_Crayons_Washable_24_crayons",
    "Hasbro_Life_Board_Game",
    "HELICOPTER",
    "Jansport_School_Backpack_Blue_Streak",
    "Kong_Puppy_Teething_Rubber_Small_Pink",
    "Netgear_N750_Wireless_Dual_Band_Gigabit_Router",
    "Nintendo_Mario_Action_Figure",
    "OXO_Soft_Works_Can_Opener_SnapLock",
    "Philips_60ct_Warm_White_LED_Smooth_Mini_String_Lights",
    "Schleich_S_Bayala_Unicorn_70432",
    "Sterilite_Caddy_Blue_Sky_17_58_x_12_58_x_9_14",
    "Tetris_Link_Game",
    "Thomas_Friends_Wooden_Railway_Talking_Thomas",
    "UGG_Classic_Tall_Womens_Boots_Grey_7",
    "Weisshai_Great_White_Shark",
]

ALL_30 = EXISTING_10 + SELECTED_20

def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))

def check_render_quality(img_path):
    try:
        img = Image.open(str(img_path)).convert("RGBA")
        arr = np.array(img)
        rgb = arr[:, :, :3]
        obj_mask = rgb.min(axis=2) <= 250
        obj_pct = obj_mask.mean() * 100
        if obj_pct < 5:
            return ("FAIL", "Object covers only %.1f%% of frame" % obj_pct)
        obj_rgb = rgb[obj_mask]
        if len(obj_rgb) == 0:
            return ("FAIL", "No object pixels found")
        white_obj = (obj_rgb.min(axis=1) > 250).mean() * 100
        black_obj = (obj_rgb.max(axis=1) < 5).mean() * 100
        if white_obj > 80:
            return ("FAIL", "Object is %.0f%% white" % white_obj)
        if black_obj > 80:
            return ("FAIL", "Object is %.0f%% black" % black_obj)
        uniq = len(np.unique(obj_rgb[np.random.choice(len(obj_rgb), min(2000, len(obj_rgb)), replace=False)].astype(np.uint8), axis=0))
        if uniq < 10:
            return ("FAIL", "Only %d unique colors (silhouette)" % uniq)
        h, w = arr.shape[:2]
        cx, cy = w // 2, h // 2
        center = obj_mask[cy-20:cy+20, cx-20:cx+20]
        if center.mean() < 0.3:
            return ("WARN", "Not centered (center coverage %.0f%%)" % (center.mean()*100))
        return ("PASS", "OK (%.0f%% coverage, %d colors)" % (obj_pct, uniq))
    except Exception as e:
        return ("FAIL", str(e))

def generate_preview(glb_path, output_png):
    try:
        mesh = trimesh.load(str(glb_path), force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            mesh = meshes[0] if meshes else mesh
        mesh.apply_translation(-mesh.centroid)
        scale = np.abs(mesh.vertices).max()
        if scale > 0:
            mesh.apply_scale(1.0 / scale)
        scene = trimesh.Scene(mesh)
        data = scene.save_image(resolution=(256, 256), visible=True)
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img.save(str(output_png))
        return True
    except Exception:
        return False

def load_mesh_safe(path):
    m = trimesh.load(str(path), force="mesh", process=False)
    if isinstance(m, trimesh.Scene):
        geoms = [g for g in m.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if geoms:
            m = geoms[0]
        else:
            m = trimesh.Trimesh()
    if not isinstance(m, trimesh.Trimesh):
        m = trimesh.Trimesh(vertices=np.array(m.vertices), faces=np.array(m.faces))
    return m

def align_with_icp(source_mesh, target_mesh, max_iterations=100):
    """Align source to target using ICP, return aligned source copy."""
    src = source_mesh.copy()
    tgt = target_mesh.copy()

    src_center = src.centroid
    tgt_center = tgt.centroid
    src.apply_translation(-src_center)
    tgt.apply_translation(-tgt_center)

    src_scale = 1.0 / (np.abs(src.vertices).max() + 1e-8)
    tgt_scale = 1.0 / (np.abs(tgt.vertices).max() + 1e-8)
    src.apply_scale(tgt_scale)
    tgt.apply_scale(tgt_scale)

    src_pts = trimesh.sample.sample_surface(src, 10000)[0]
    tgt_pts = trimesh.sample.sample_surface(tgt, 10000)[0]

    try:
        matrix, transformed, info = trimesh.registration.icp(
            src_pts, tgt_pts,
            initial=np.eye(4),
            threshold=1e-5,
            max_iterations=max_iterations
        )
        aligned = src.copy()
        aligned.apply_transform(matrix)
        return aligned, tgt, True
    except Exception:
        return src, tgt, False

def compute_metrics(pred_mesh, gt_mesh, num_samples=50000, threshold=0.01):
    pred_pts = trimesh.sample.sample_surface(pred_mesh, num_samples)[0]
    gt_pts = trimesh.sample.sample_surface(gt_mesh, num_samples)[0]

    pred_tree = KDTree(pred_pts)
    gt_tree = KDTree(gt_pts)

    d_p2g, _ = gt_tree.query(pred_pts)
    d_g2p, _ = pred_tree.query(gt_pts)

    cd_forward = float(np.mean(d_p2g))
    cd_backward = float(np.mean(d_g2p))
    cd_symmetric = cd_forward + cd_backward

    cd_squared_forward = float(np.mean(d_p2g ** 2))
    cd_squared_backward = float(np.mean(d_g2p ** 2))
    cd_squared = cd_squared_forward + cd_squared_backward

    precision = float(np.mean(d_p2g < threshold))
    recall = float(np.mean(d_g2p < threshold))
    f_score = 2 * precision * recall / (precision + recall + 1e-10)

    return {
        "chamfer_distance_unsquared": round(cd_symmetric, 6),
        "chamfer_distance_forward": round(cd_forward, 6),
        "chamfer_distance_backward": round(cd_backward, 6),
        "chamfer_distance_squared": round(cd_squared, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f_score": round(f_score, 6),
        "threshold": threshold,
        "num_samples": num_samples,
        "pred_vertices": len(pred_mesh.vertices),
        "gt_vertices": len(gt_mesh.vertices),
    }

def render_comparison(gt_mesh, pred_mesh, oid, output_path):
    """Render side-by-side comparison: GT left, prediction right."""
    try:
        gt = gt_mesh.copy()
        pred = pred_mesh.copy()
        gt.apply_translation(-gt.centroid)
        pred.apply_translation(-pred.centroid)
        max_extent = max(np.abs(gt.vertices).max(), np.abs(pred.vertices).max(), 1e-6)
        gt.apply_scale(1.0 / max_extent)
        pred.apply_scale(1.0 / max_extent)

        gt_scene = trimesh.Scene(gt)
        pred_scene = trimesh.Scene(pred)
        gt_data = gt_scene.save_image(resolution=(512, 512), visible=True)
        pred_data = pred_scene.save_image(resolution=(512, 512), visible=True)

        gt_img = Image.open(io.BytesIO(gt_data)).convert("RGB")
        pred_img = Image.open(io.BytesIO(pred_data)).convert("RGB")

        side_by_side = Image.new("RGB", (1024, 512))
        side_by_side.paste(gt_img, (0, 0))
        side_by_side.paste(pred_img, (512, 0))
        side_by_side.save(str(output_path))
        return True
    except Exception as e:
        log("  Render failed for %s: %s" % (oid, e))
        return False

# ===== STEP 1: Run inference on 20 new samples =====
def run_inference():
    log("=" * 70)
    log("STEP 1: TripoSR inference on %d new GSO samples" % len(SELECTED_20))
    log("=" * 70)

    tripo = LocalTripoService()
    tripo._load_model()

    log_path = LOG_DIR / "triposr_30.csv"
    all_results = []

    if log_path.exists():
        with open(str(log_path), "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                all_results.append(r)
        log("Loaded %d existing results from CSV" % len(all_results))

    completed_ids = {r["object_id"] for r in all_results if r.get("status") == "success"}
    attempted_ids = {r["object_id"] for r in all_results}

    for idx, oid in enumerate(EXISTING_10):
        if oid in completed_ids or oid in attempted_ids:
            log("[%d/30] %s — SKIP (already in CSV)" % (idx + 1, oid))
            continue
        # Copy pilot output
        pilot_dir = PILOT_OUTPUT_DIR / oid
        target_dir = OUTPUT_DIR / oid
        if pilot_dir.exists():
            import shutil
            shutil.copytree(str(pilot_dir), str(target_dir), dirs_exist_ok=True)
            glb_path = target_dir / ("%s.glb" % oid)
            glb_sz = glb_path.stat().st_size if glb_path.exists() else 0
            entry = OrderedDict([
                ("object_id", oid), ("status", "success"), ("inference_time_s", ""),
                ("vram_peak_mb", ""), ("vertices", ""), ("faces", ""),
                ("glb_size_mb", round(glb_sz / 1e6, 2) if glb_sz > 0 else ""),
                ("source", "pilot_copy"),
            ])
            all_results.append(dict(entry))
            log("[%d/30] %s — copied from pilot" % (idx + 1, oid))

    for idx, oid in enumerate(SELECTED_20):
        seq = len(EXISTING_10) + idx + 1
        if oid in completed_ids:
            log("[%d/30] %s — SKIP (already completed)" % (seq, oid))
            continue

        log("[%d/30] %s ..." % (seq, oid))
        render_path = GSO_DIR / oid / "renders" / "front.png"
        sample_dir = OUTPUT_DIR / oid
        sample_dir.mkdir(parents=True, exist_ok=True)

        if not render_path.exists():
            log("  FAIL: render not found")
            all_results.append({"object_id": oid, "status": "failed", "error": "render_not_found", "source": "new"})
            continue

        status, msg = check_render_quality(render_path)
        if status == "FAIL":
            log("  FAIL: %s" % msg)
            all_results.append({"object_id": oid, "status": "failed", "error": msg, "source": "new"})
            continue

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
        except Exception as e:
            log("  FAIL: inference crashed: %s" % e)
            all_results.append({"object_id": oid, "status": "failed", "error": str(e), "source": "new"})
            continue

        glb_path = sample_dir / ("%s.glb" % oid)
        glb_sz = glb_path.stat().st_size if glb_path.exists() else 0
        verts = result.get("vertices", 0)
        faces = result.get("faces", 0)
        entry = OrderedDict([
            ("object_id", oid), ("status", "success"), ("inference_time_s", round(elapsed, 1)),
            ("vram_peak_mb", round(vram_peak, 0)), ("vertices", verts), ("faces", faces),
            ("glb_size_mb", round(glb_sz / 1e6, 2)), ("source", "new"),
        ])
        all_results.append(dict(entry))
        log("  Time: %.1f s, VRAM: %.0f MB, Mesh: %d verts/%d faces, GLB: %.2f MB"
            % (elapsed, vram_peak, verts, faces, glb_sz / 1e6))

        # Save incrementally
        with open(str(log_path), "w", newline="", encoding="utf-8-sig") as f:
            fields = ["object_id", "status", "inference_time_s", "vram_peak_mb", "vertices", "faces", "glb_size_mb", "source", "error"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows([{k: r.get(k, "") for k in fields} for r in all_results])

    success = [r for r in all_results if r.get("status") == "success"]
    failed = [r for r in all_results if r.get("status") == "failed"]
    log("Inference done: %d success, %d failed / %d total" % (len(success), len(failed), len(ALL_30)))
    return all_results

# ===== STEP 2: ICP-aligned geometry metrics =====
def compute_all_metrics():
    log("=" * 70)
    log("STEP 2: ICP-aligned geometry metrics for all 30 samples")
    log("=" * 70)

    results = {}
    for idx, oid in enumerate(ALL_30):
        log("[%d/30] %s ..." % (idx + 1, oid))

        # Try prediction output dirs
        pred_paths = [
            OUTPUT_DIR / oid / ("%s.glb" % oid),
            OUTPUT_DIR / oid / ("%s_raw.glb" % oid),
            PILOT_OUTPUT_DIR / oid / ("%s.glb" % oid),
            PILOT_OUTPUT_DIR / oid / ("%s_raw.glb" % oid),
        ]
        pred_path = None
        for p in pred_paths:
            if p.exists():
                pred_path = p
                break

        if pred_path is None:
            log("  SKIP: no prediction mesh found")
            results[oid] = {"error": "no prediction mesh"}
            continue

        gt_path = GSO_DIR / oid / "model.obj"
        if not gt_path.exists():
            # Try GLB
            gt_path = GSO_DIR / oid / "model.glb"
        if not gt_path.exists():
            log("  SKIP: no GT mesh")
            results[oid] = {"error": "no GT mesh"}
            continue

        try:
            pred_mesh = load_mesh_safe(pred_path)
            gt_mesh = load_mesh_safe(gt_path)

            if len(pred_mesh.vertices) < 10 or len(gt_mesh.vertices) < 10:
                log("  SKIP: degenerate mesh")
                results[oid] = {"error": "degenerate mesh"}
                continue

            # ICP alignment
            pred_aligned, gt_aligned, icp_ok = align_with_icp(pred_mesh, gt_mesh)

            # Metrics (both with and without ICP)
            metrics = compute_metrics(pred_aligned, gt_aligned)
            metrics["icp_applied"] = icp_ok
            metrics["icp_iterations"] = 100 if icp_ok else 0

            results[oid] = metrics
            log("  CD=%.6f, F=%.4f, ICP=%s" % (metrics["chamfer_distance_unsquared"], metrics["f_score"], icp_ok))

            # Generate comparison image
            comp_path = COMPARISON_DIR / ("comp_%s.png" % oid)
            render_comparison(gt_mesh, pred_mesh, oid, comp_path)

        except Exception as e:
            log("  ERROR: %s" % e)
            results[oid] = {"error": str(e)}

    # Save metrics
    metrics_path = METRICS_DIR / "geometry_metrics_30.json"
    with open(str(metrics_path), "w") as f:
        json.dump(results, f, indent=2)
    log("Metrics saved to %s" % metrics_path)

    # Generate summary
    valid = {k: v for k, v in results.items() if "error" not in v}
    log("\n" + "=" * 120)
    log("  GEOMETRY METRICS SUMMARY — %d valid / %d total" % (len(valid), len(results)))
    log("=" * 120)
    header = f"{'Object ID':55s} {'CD(unsq)':>10s} {'CD(sq)':>10s} {'Prec':>7s} {'Rec':>7s} {'F-sc':>7s} {'ICP':>5s} {'#PredV':>8s} {'#GTV':>8s}"
    log(header)
    log("-" * len(header))

    cd_vals = []
    f_vals = []
    p_vals = []
    r_vals = []
    for oid in ALL_30:
        m = results.get(oid, {})
        if "error" in m:
            log(f"{oid:55s} {'ERROR':>10s} - {m['error']}")
        else:
            log(f"{oid:55s} {m['chamfer_distance_unsquared']:10.4f} {m['chamfer_distance_squared']:10.4f} {m['precision']:7.4f} {m['recall']:7.4f} {m['f_score']:7.4f} {str(m['icp_applied']):>5s} {m['pred_vertices']:8d} {m['gt_vertices']:8d}")
            cd_vals.append(m['chamfer_distance_unsquared'])
            f_vals.append(m['f_score'])
            p_vals.append(m['precision'])
            r_vals.append(m['recall'])

    if cd_vals:
        log("-" * len(header))
        log(f"{'MEAN':55s} {np.mean(cd_vals):10.4f} {np.mean([v['chamfer_distance_squared'] for v in valid.values()]):10.4f} {np.mean(p_vals):7.4f} {np.mean(r_vals):7.4f} {np.mean(f_vals):7.4f}")
        log(f"{'STD':55s} {np.std(cd_vals):10.4f} {'':10s} {np.std(p_vals):7.4f} {np.std(r_vals):7.4f} {np.std(f_vals):7.4f}")
        log(f"{'MIN':55s} {min(cd_vals):10.4f} {'':10s} {min(p_vals):7.4f} {min(r_vals):7.4f} {min(f_vals):7.4f}")
        log(f"{'MAX':55s} {max(cd_vals):10.4f} {'':10s} {max(p_vals):7.4f} {max(r_vals):7.4f} {max(f_vals):7.4f}")

    # Generate LaTeX table
    latex_lines = [
        "%% Auto-generated geometry metrics table for 30 GSO samples",
        "%% Generated: %s" % now_str(),
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Kết quả metric hình học trên 30 mẫu GSO (sau ICP)}",
        "\\label{tab:geometry-metrics-30}",
        "\\scriptsize",
        "\\renewcommand{\\arraystretch}{1.0}",
        "\\begin{tabularx}{\\textwidth}{l C{0.9cm} C{0.9cm} C{0.7cm} C{0.7cm} C{0.7cm}}",
        "\\toprule",
        "\\textbf{Mẫu} & \\textbf{CD$\\downarrow$} & \\textbf{CD$^2$$\\downarrow$} & \\textbf{P$\\uparrow$} & \\textbf{R$\\uparrow$} & \\textbf{F$\\uparrow$} \\\\",
        "\\midrule",
    ]
    for oid in ALL_30:
        m = results.get(oid, {})
        if "error" not in m:
            short = oid.replace("_", " ")[:25]
            latex_lines.append("    %s & %.4f & %.4f & %.3f & %.3f & %.3f \\\\" % (
                short, m["chamfer_distance_unsquared"], m["chamfer_distance_squared"],
                m["precision"], m["recall"], m["f_score"]))
    latex_lines.append("\\midrule")
    latex_lines.append("    \\textbf{Trung bình} & %.4f & %.4f & %.3f & %.3f & %.3f \\\\" % (
        np.mean(cd_vals), np.mean([v['chamfer_distance_squared'] for v in valid.values()]),
        np.mean(p_vals), np.mean(r_vals), np.mean(f_vals)))
    latex_lines.append("    \\textbf{Độ lệch chuẩn} & %.4f & & %.3f & %.3f & %.3f \\\\" % (
        np.std(cd_vals), np.std(p_vals), np.std(r_vals), np.std(f_vals)))
    latex_lines.append("\\bottomrule")
    latex_lines.append("\\end{tabularx}")
    latex_lines.append("\\end{table}")

    latex_path = METRICS_DIR / "geometry_metrics_30_table.tex"
    with open(str(latex_path), "w") as f:
        f.write("\n".join(latex_lines))
    log("LaTeX table saved to %s" % latex_path)

    # Save summary JSON
    summary = {
        "n_total": len(results),
        "n_valid": len(valid),
        "n_failed": len(results) - len(valid),
        "mean_cd": round(float(np.mean(cd_vals)), 6),
        "std_cd": round(float(np.std(cd_vals)), 6),
        "mean_f_score": round(float(np.mean(f_vals)), 6),
        "std_f_score": round(float(np.std(f_vals)), 6),
        "mean_precision": round(float(np.mean(p_vals)), 6),
        "mean_recall": round(float(np.mean(r_vals)), 6),
    }
    with open(str(METRICS_DIR / "geometry_metrics_30_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    log("Summary: %s" % json.dumps(summary, indent=2))

    return results


if __name__ == "__main__":
    log("GSO Experiment 30 — Version %s" % SCRIPT_VERSION)
    log("Project root: %s" % PROJECT_ROOT)
    log("GSO dir: %s" % GSO_DIR)
    log("Output dir: %s" % OUTPUT_DIR)

    # Step 1: Run inference
    run_inference()

    # Step 2: Compute metrics + comparison images
    compute_all_metrics()

    log("=" * 70)
    log("DONE. Results:")
    log("  Metrics:     %s" % (METRICS_DIR / "geometry_metrics_30.json"))
    log("  LaTeX table: %s" % (METRICS_DIR / "geometry_metrics_30_table.tex"))
    log("  Summary:     %s" % (METRICS_DIR / "geometry_metrics_30_summary.json"))
    log("  Comparisons: %s/*" % COMPARISON_DIR)
    log("=" * 70)
