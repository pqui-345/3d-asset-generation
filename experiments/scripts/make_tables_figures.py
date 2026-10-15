import os, sys, json, csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from experiments.utils.common import set_seed, setup_logger


def load_metrics(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_classification_table(metrics_dir: str, output_dir: str):
    rows = []
    for fname in os.listdir(metrics_dir):
        if fname.endswith("_metrics.json") and fname != "triposr_metrics.json":
            path = os.path.join(metrics_dir, fname)
            m = load_metrics(path)
            if "results" in m:
                for r in m["results"]:
                    rows.append({
                        "Method": r["model"].upper(),
                        "Accuracy": f"{r['accuracy']['mean']:.4f} ± {r['accuracy']['std']:.4f}",
                        "Precision": f"{r['precision']['mean']:.4f} ± {r['precision']['std']:.4f}",
                        "Recall": f"{r['recall']['mean']:.4f} ± {r['recall']['std']:.4f}",
                        "F1-score": f"{r['f1']['mean']:.4f} ± {r['f1']['std']:.4f}",
                    })
            else:
                rows.append({
                    "Method": m.get("experiment", fname.replace("_metrics.json", "")),
                    "Accuracy": f"{m.get('accuracy', 0):.4f}",
                    "Precision": f"{m.get('precision', 0):.4f}",
                    "Recall": f"{m.get('recall', 0):.4f}",
                    "F1-score": f"{m.get('f1', 0):.4f}",
                })

    os.makedirs(output_dir, exist_ok=True)

    latex = r"""\begin{table}[ht]
\centering
\caption{Kết quả phân loại trên bộ dữ liệu thực nghiệm}
\label{tab:classification_results}
\begin{tabular}{lcccc}
\toprule
Phương pháp & Accuracy & Precision & Recall & F1-score \\
\midrule
"""
    for r in rows:
        latex += f"{r['Method']} & {r['Accuracy']} & {r['Precision']} & {r['Recall']} & {r['F1-score']} \\\\\n"
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    with open(os.path.join(output_dir, "classification_table.tex"), "w", encoding="utf-8") as f:
        f.write(latex)

    csv_path = os.path.join(output_dir, "classification_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return rows


def make_triposr_table(metrics_path: str, output_dir: str):
    m = load_metrics(metrics_path)
    if "error" in m:
        print("TripoSR metrics not available:", m.get("error"))
        return

    latex = r"""\begin{table}[ht]
\centering
\caption{Kết quả đánh giá TripoSR trên bộ dữ liệu thực nghiệm}
\label{tab:triposr_results}
\begin{tabular}{lcccc}
\toprule
Chỉ số & Giá trị \\
\midrule
"""
    key_map = {
        "inference_time_cold_mean_s": "Thời gian inference (cold start, s)",
        "inference_time_cold_std_s": "Độ lệch chuẩn cold start (s)",
        "inference_time_warm_mean_s": "Thời gian inference (warm start, s)",
        "vertices_mean": "Số đỉnh trung bình",
        "faces_mean": "Số mặt trung bình",
        "samples_succeeded": "Số mẫu thành công",
        "samples_failed": "Số mẫu thất bại",
    }
    for key, label in key_map.items():
        if key in m and m[key] is not None:
            val = m[key]
            if isinstance(val, float):
                latex += f"{label} & {val:.3f} \\\\\n"
            else:
                latex += f"{label} & {val} \\\\\n"
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "triposr_table.tex"), "w", encoding="utf-8") as f:
        f.write(latex)


def make_augmentation_summary(metrics_dir: str, output_dir: str):
    aug_results = []
    for fname in os.listdir(metrics_dir):
        if fname.startswith("augmentation_") and fname.endswith("_metrics.json"):
            path = os.path.join(metrics_dir, fname)
            m = load_metrics(path)
            aug_results.append({
                "Config": m.get("experiment", fname),
                "Accuracy": f"{m.get('accuracy', 0):.4f}",
                "Augmentation": json.dumps(m.get("config", {}).get("augmentation", {}), ensure_ascii=False),
            })

    if not aug_results:
        return

    latex = r"""\begin{table}[ht]
\centering
\caption{Kết quả ablation augmentation}
\label{tab:augmentation_ablation}
\begin{tabular}{lcc}
\toprule
Cấu hình & Accuracy & Augmentation \\
\midrule
"""
    for r in aug_results:
        latex += f"{r['Config']} & {r['Accuracy']} & {r['Augmentation']} \\\\\n"
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    with open(os.path.join(output_dir, "augmentation_table.tex"), "w", encoding="utf-8") as f:
        f.write(latex)


def main():
    logger = setup_logger("make_tables", "experiments/outputs/logs/make_tables.log")
    metrics_dir = "experiments/outputs/metrics"
    output_dir = "experiments/outputs/tables"

    logger.info("Generating classification table...")
    rows = make_classification_table(metrics_dir, output_dir)
    if rows:
        for r in rows:
            logger.info("  %s: acc=%s", r["Method"], r["Accuracy"])

    logger.info("Generating TripoSR table...")
    make_triposr_table(os.path.join(metrics_dir, "triposr_metrics.json"), output_dir)

    logger.info("Generating augmentation table...")
    make_augmentation_summary(metrics_dir, output_dir)

    logger.info("Tables saved to %s", output_dir)


if __name__ == "__main__":
    main()
