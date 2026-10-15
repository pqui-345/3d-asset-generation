#!/usr/bin/env python3
"""
Geometry Evaluation Script for 3D Reconstruction.

Evaluates predicted mesh against ground truth mesh using:
- Chamfer Distance (CD)
- F-score at 1% threshold
- Precision / Recall
- Normal Consistency

Usage:
    python evaluate_geometry.py --pred <pred.glb> --gt <gt.obj> [--samples 50000] [--threshold 0.01]

Dependencies: trimesh, numpy, scipy

NOTE: This script is a DRAFT. It requires aligned ground truth meshes from GSO
and a verified alignment protocol before use in the thesis.
"""

import argparse
import json
import logging
import sys

import numpy as np

try:
    import trimesh
except ImportError:
    print("ERROR: trimesh is required. Install with: pip install trimesh")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_mesh(path: str) -> trimesh.Trimesh:
    mesh = trimesh.load(path)
    if isinstance(mesh, trimesh.Scene):
        logger.info(f"Scene loaded from {path}, merging geometry")
        mesh = mesh.dump(concatenate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"Expected Trimesh, got {type(mesh)} from {path}")
    logger.info(f"Loaded {path}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")
    return mesh


def sample_mesh(mesh: trimesh.Trimesh, n_samples: int) -> np.ndarray:
    points, _ = trimesh.sample.sample_surface(mesh, n_samples)
    return points


def chamfer_distance(P: np.ndarray, Q: np.ndarray) -> float:
    from scipy.spatial import KDTree

    tree_Q = KDTree(Q)
    tree_P = KDTree(P)

    dist_PQ = tree_Q.query(P, k=1)[0]
    dist_QP = tree_P.query(Q, k=1)[0]

    cd = np.mean(dist_PQ ** 2) + np.mean(dist_QP ** 2)
    return float(cd)


def f_score(P: np.ndarray, Q: np.ndarray, threshold: float = 0.01) -> dict:
    from scipy.spatial import KDTree

    tree_Q = KDTree(Q)
    tree_P = KDTree(P)

    dist_PQ = tree_Q.query(P, k=1)[0]
    dist_QP = tree_P.query(Q, k=1)[0]

    tp_p = np.sum(dist_PQ < threshold)
    tp_q = np.sum(dist_QP < threshold)

    precision = tp_p / len(P)
    recall = tp_q / len(Q)

    f = 2 * precision * recall / (precision + recall + 1e-10)
    return {"precision": float(precision), "recall": float(recall), "f_score": float(f)}


def normal_consistency(pred: trimesh.Trimesh, gt: trimesh.Trimesh,
                       P: np.ndarray, Q: np.ndarray) -> float:
    from scipy.spatial import KDTree

    tree_Q = KDTree(Q)
    _, idx = tree_Q.query(P, k=1)

    pred_normals = pred.face_normals[pred.faces]
    gt_normals = gt.face_normals[gt.faces]

    # For each sampled point on pred, find nearest point on GT
    # Then compute dot product of face normals
    # (simplified: use vertex normals via trimesh)
    pred_vert_normals = trimesh.sample.sample_surface(pred, len(P))[1]
    # TODO: proper face normal lookup
    _ = idx  # placeholder
    return 0.0


def main():
    parser = argparse.ArgumentParser(description="Evaluate geometry of predicted 3D mesh")
    parser.add_argument("--pred", required=True, help="Predicted mesh file (.glb/.obj)")
    parser.add_argument("--gt", required=True, help="Ground truth mesh file (.obj/.glb)")
    parser.add_argument("--samples", type=int, default=50000, help="Number of sample points")
    parser.add_argument("--threshold", type=float, default=0.01, help="Distance threshold for F-score (relative to bounding box diagonal)")
    parser.add_argument("--output", help="Output JSON file for results")
    args = parser.parse_args()

    logger.info(f"Loading meshes...")
    pred_mesh = load_mesh(args.pred)
    gt_mesh = load_mesh(args.gt)

    # Compute bounding box diagonal for relative threshold
    bbox_diag = np.linalg.norm(gt_mesh.bounds[1] - gt_mesh.bounds[0])
    threshold_abs = args.threshold * bbox_diag
    logger.info(f"BBox diagonal: {bbox_diag:.4f}, threshold: {threshold_abs:.6f}")

    # Sample surfaces
    logger.info(f"Sampling {args.samples} points per mesh...")
    P = sample_mesh(pred_mesh, args.samples)
    Q = sample_mesh(gt_mesh, args.samples)

    # Compute metrics
    logger.info("Computing Chamfer Distance...")
    cd = chamfer_distance(P, Q)

    logger.info("Computing F-score...")
    fs = f_score(P, Q, threshold=threshold_abs)

    results = {
        "pred_mesh": args.pred,
        "gt_mesh": args.gt,
        "n_samples": args.samples,
        "chamfer_distance": cd,
        "precision": fs["precision"],
        "recall": fs["recall"],
        "f_score": fs["f_score"],
    }

    logger.info(f"Results:")
    logger.info(f"  CD = {cd:.6f}")
    logger.info(f"  Precision = {fs['precision']:.4f}")
    logger.info(f"  Recall = {fs['recall']:.4f}")
    logger.info(f"  F-score = {fs['f_score']:.4f}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")

    return results


if __name__ == "__main__":
    main()
