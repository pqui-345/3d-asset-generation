#!/usr/bin/env python
"""Evaluate geometry metrics on GSO predictions vs ground truth."""
import os, sys, json, csv
import numpy as np
import trimesh
from scipy.spatial import KDTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def compute_metrics(pred_mesh, gt_mesh, num_samples=50000, threshold=0.01):
    pred_pts = trimesh.sample.sample_surface(pred_mesh, num_samples)[0]
    gt_pts = trimesh.sample.sample_surface(gt_mesh, num_samples)[0]

    pred_tree = KDTree(pred_pts)
    gt_tree = KDTree(gt_pts)

    dist_pred_to_gt, _ = gt_tree.query(pred_pts)
    dist_gt_to_pred, _ = pred_tree.query(gt_pts)
    cd = np.mean(dist_pred_to_gt) + np.mean(dist_gt_to_pred)

    precision = np.mean(dist_pred_to_gt < threshold)
    recall = np.mean(dist_gt_to_pred < threshold)
    f_score = 2 * precision * recall / (precision + recall + 1e-10)

    return {
        "chamfer_distance": float(cd),
        "precision": float(precision),
        "recall": float(recall),
        "f_score": float(f_score),
        "threshold": threshold,
        "num_samples": num_samples,
        "pred_vertices": len(pred_mesh.vertices),
        "gt_vertices": len(gt_mesh.vertices)
    }

def align_meshes(pred_mesh, gt_mesh):
    pred_center = pred_mesh.centroid
    gt_center = gt_mesh.centroid

    pred_aligned = pred_mesh.copy()
    pred_aligned.apply_translation(-pred_center)

    gt_aligned = gt_mesh.copy()
    gt_aligned.apply_translation(-gt_center)

    gt_scale = 1.0 / gt_aligned.bounding_box.extents.max()
    gt_aligned.apply_scale(gt_scale)
    pred_aligned.apply_scale(gt_scale)

    return pred_aligned, gt_aligned

# Read actual object IDs from the pilot CSV
pilot_ids = []
with open("experiments/logs/triposr_pilot.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pilot_ids.append(row["object_id"])

results = {}
for oid in pilot_ids:
    pred_search = f"experiments/outputs/predictions/triposr_pilot/{oid}/{oid}.glb"
    pred_raw_search = f"experiments/outputs/predictions/triposr_pilot/{oid}/{oid}_raw.glb"
    gt_path = f"static/templates/gso/{oid}/model.obj"

    pred_path = None
    if os.path.exists(pred_search):
        pred_path = pred_search
    elif os.path.exists(pred_raw_search):
        pred_path = pred_raw_search

    if pred_path is None:
        print(f"SKIP {oid}: no prediction mesh found")
        results[oid] = {"error": "no prediction mesh"}
        continue

    if not os.path.exists(gt_path):
        print(f"SKIP {oid}: no GT mesh at {gt_path}")
        results[oid] = {"error": "no GT mesh"}
        continue

    try:
        pred_mesh = trimesh.load(pred_path)
        gt_mesh = trimesh.load(gt_path)

        if not isinstance(pred_mesh, trimesh.Trimesh):
            if hasattr(pred_mesh, 'geometry'):
                pred_mesh = pred_mesh.to_geometry()
            else:
                pred_mesh = trimesh.Trimesh(vertices=pred_mesh.vertices, faces=pred_mesh.faces)

        if not isinstance(gt_mesh, trimesh.Trimesh):
            if hasattr(gt_mesh, 'geometry'):
                gt_mesh = gt_mesh.to_geometry()
            else:
                gt_mesh = trimesh.Trimesh(vertices=gt_mesh.vertices, faces=gt_mesh.faces)

        pred_aligned, gt_aligned = align_meshes(pred_mesh, gt_mesh)
        metrics = compute_metrics(pred_aligned, gt_aligned)
        results[oid] = metrics
        print(f"OK {oid}: CD={metrics['chamfer_distance']:.6f}, F={metrics['f_score']:.4f}")

    except Exception as e:
        print(f"ERROR {oid}: {e}")
        results[oid] = {"error": str(e)}

os.makedirs("experiments/outputs/metrics", exist_ok=True)
with open("experiments/outputs/metrics/geometry_metrics.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 80)
print("  GEOMETRY METRICS SUMMARY")
print("=" * 80)
print(f"{'Object ID':55s} {'CD':>10s} {'Prec':>6s} {'Recall':>6s} {'F-score':>8s} {'#PredV':>8s} {'#GTV':>8s}")
print("-" * 101)
for oid, m in results.items():
    if "error" in m:
        print(f"{oid:55s} {'ERROR':>10s} - {m['error']}")
    else:
        print(f"{oid:55s} {m['chamfer_distance']:10.4f} {m['precision']:6.3f} {m['recall']:6.3f} {m['f_score']:8.3f} {m['pred_vertices']:8d} {m['gt_vertices']:8d}")
print("=" * 80)
