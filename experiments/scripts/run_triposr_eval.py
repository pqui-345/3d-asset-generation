import os, sys, argparse, csv, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import torch
import numpy as np

from experiments.utils.common import set_seed, load_config, get_device, setup_logger, Timer, save_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/configs/triposr_eval.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["experiment"]["seed"])
    logger = setup_logger("triposr_eval", "experiments/outputs/logs/triposr_eval.log")
    device = get_device()
    logger.info("Device: %s", device)

    with open(cfg["data"]["manifest"], "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if cfg["data"].get("sample_limit"):
        rows = rows[:cfg["data"]["sample_limit"]]

    try:
        from services.local_tripo_service import LocalTripoService
        from services.bg_remover import BGRemoverService
        tripo_service = LocalTripoService()
        bg_remover = BGRemoverService()
    except Exception as e:
        logger.error("Failed to init TripoSR: %s", e)
        save_metrics(cfg["output"]["metrics_file"], {"error": str(e), "status": "service_init_failed"})
        return

    output_dir = "experiments/outputs/predictions/triposr"
    os.makedirs(output_dir, exist_ok=True)

    results = []
    for idx, row in enumerate(rows):
        uid = row["uid"]
        img_path = row.get("image_path", "")
        if not img_path or not os.path.exists(img_path):
            logger.warning("[%d/%d] %s: image not found, skipping", idx + 1, len(rows), uid)
            continue

        logger.info("[%d/%d] %s", idx + 1, len(rows), uid)
        sample_dir = os.path.join(output_dir, uid)
        os.makedirs(sample_dir, exist_ok=True)

        cold_time = None
        warm_time = None

        from PIL import Image
        img = Image.open(img_path).convert("RGB")
        no_bg = bg_remover.remove_background(img)
        no_bg_path = os.path.join(sample_dir, "no_bg.png")
        no_bg.save(no_bg_path)

        try:
            with Timer() as t:
                result = tripo_service.generate_3d([no_bg_path], sample_dir, f"eval_{uid}")
            cold_time = t.elapsed
            logger.info("  cold inference: %s", t)
        except Exception as e:
            logger.error("  cold inference failed: %s", e)
            cold_time = None

        if cold_time is not None and result:
            warm_times = []
            for w in range(cfg["triposr"].get("warmup_runs", 3)):
                try:
                    with Timer() as t:
                        tripo_service.generate_3d([no_bg_path], sample_dir, f"eval_{uid}_w{w}")
                    warm_times.append(t.elapsed)
                    logger.info("  warm run %d: %s", w + 1, t)
                except Exception as e:
                    logger.error("  warm run %d failed: %s", w + 1, e)
            if warm_times:
                warm_time = float(np.mean(warm_times))

            res = {
                "uid": uid,
                "status": "success",
                "inference_time_cold_s": round(cold_time, 3) if cold_time else None,
                "inference_time_warm_avg_s": round(warm_time, 3) if warm_time else None,
                "vertices": result.get("vertices", 0),
                "faces": result.get("faces", 0),
                "file_size_mb": result.get("file_size", "0"),
                "glb_path": result.get("glb_path", ""),
            }
        else:
            res = {"uid": uid, "status": "failed"}

        results.append(res)

    metrics = {
        "experiment": "triposr_evaluation",
        "samples_attempted": len(rows),
        "samples_succeeded": sum(1 for r in results if r.get("status") == "success"),
        "samples_failed": sum(1 for r in results if r.get("status") == "failed"),
    }
    if any(r.get("inference_time_cold_s") for r in results):
        cold_times = [r["inference_time_cold_s"] for r in results if r.get("inference_time_cold_s")]
        warm_times = [r["inference_time_warm_avg_s"] for r in results if r.get("inference_time_warm_avg_s")]
        vertices = [r["vertices"] for r in results if r.get("vertices")]
        faces = [r["faces"] for r in results if r.get("faces")]
        metrics.update({
            "inference_time_cold_mean_s": float(np.mean(cold_times)),
            "inference_time_cold_std_s": float(np.std(cold_times)),
            "inference_time_warm_mean_s": float(np.mean(warm_times)) if warm_times else None,
            "vertices_mean": float(np.mean(vertices)),
            "faces_mean": float(np.mean(faces)),
        })

    save_metrics(cfg["output"]["metrics_file"], metrics)

    csv_path = cfg["output"]["log_file"]
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    logger.info(json.dumps(metrics, indent=2))
    logger.info("Done. Log: %s, Metrics: %s", csv_path, cfg["output"]["metrics_file"])


if __name__ == "__main__":
    main()
