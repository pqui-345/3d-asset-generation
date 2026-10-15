"""
Experiment Runner for graduation thesis benchmarking.
Tests all 20 images across available methods, logs to CSV.
"""
import os, sys, csv, time, json
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

import torch
import numpy as np
from PIL import Image
from services.recognition_service import RecognitionService
from services.retrieval_service import RetrievalService
from services.template_database import TemplateDatabase
from services.deformation_service import DeformationService
from services.texture_transfer_service import TextureTransferService
from services.template_service import TemplateService
from services.mesh_generator import MeshGeneratorService
from services.bg_remover import BGRemoverService

OUTPUT = "data/experiment_results.csv"
IMG_DIR = "static/uploads/experiment"
MODELS_DIR = "static/models/experiment"
os.makedirs(MODELS_DIR, exist_ok=True)

# Test inputs: (name, file, expected_category)
TEST_IMAGES = [
    ("hinh_tron",     "hinh_tron.png",     "geometry"),
    ("hinh_vuong",    "hinh_vuong.png",    "geometry"),
    ("hinh_tamgiac",  "hinh_tamgiac.png",  "geometry"),
    ("hinh_sao",      "hinh_sao.png",      "geometry"),
    ("hinh_lucgiac",  "hinh_lucgiac.png",  "geometry"),
    ("qua_tao",       "qua_tao.png",       "botany"),
    ("qua_chuoi",     "qua_chuoi.png",     "botany"),
    ("trai_cam",      "trai_cam.png",      "botany"),
    ("cai_coc",       "cai_coc.png",       "lab"),
    ("chai_nuoc",     "chai_nuoc.png",     "lab"),
    ("quyen_sach",    "quyen_sach.png",    "tools"),
    ("cay_viet",      "cay_viet.png",      "tools"),
    ("thuoc_ke",      "thuoc_ke.png",      "tools"),
    ("qua_dia",       "qua_dia.png",       "earth"),
    ("binh_cau",      "binh_cau.png",      "chemistry"),
    ("banh_rang",     "banh_rang.png",     "physics"),
    ("mach_dien",     "mach_dien.png",     "physics"),
    ("phan_tu",       "phan_tu.png",       "chemistry"),
    ("chiec_la",      "chiec_la.png",      "botany"),
    ("bong_hoa",      "bong_hoa.png",      "botany"),
]

def run_template_method(name, img, img_path, ts, slug):
    """Run template retrieval + deformation, return metrics dict."""
    row = {"method": "template_retrieval"}
    t0 = time.time()
    try:
        recog = ts.recognition.recognize(img)
        row["clip_category"] = recog["category"]
        row["clip_confidence"] = round(recog["confidence"], 4)
        row["clip_top5"] = json.dumps([(c,round(float(s),4)) for c,s in recog["top5"]], ensure_ascii=True)

        # Search
        candidates = ts.retrieval.search(recog["embedding"], k=5)
        if not candidates:
            row["status"] = "no_template_found"
            row["time_s"] = round(time.time()-t0, 3)
            return row

        best = candidates[0]
        row["template_name"] = best["name"].encode("ascii", "ignore").decode()
        row["template_uid"] = best["uid"]
        row["similarity"] = round(best["similarity"], 4)
        row["template_path"] = best.get("glb_path","")

        if best["similarity"] < 0.75:
            row["status"] = "sim_below_threshold"
            row["time_s"] = round(time.time()-t0, 3)
            return row

        cargs = ts.generate_3d(img, img_path, None, MODELS_DIR, slug)
        row["status"] = "success"
        row["vertices"] = cargs.get("vertices", 0)
        row["faces"] = cargs.get("faces", 0)
        row["texture_size"] = cargs.get("texture_size", "N/A")
        row["file_size_mb"] = cargs.get("file_size", "0 MB")
        row["time_s"] = round(cargs.get("inference_time", time.time()-t0), 3)
        row["glb_output"] = cargs.get("glb_path", "")

    except Exception as e:
        row["status"] = f"error: {str(e)[:100]}"
        row["time_s"] = round(time.time()-t0, 3)
    return row


def run_procedural_method(name, img_path, slug, style):
    """Run procedural generation, return metrics dict."""
    row = {"method": f"procedural_{style}"}
    t0 = time.time()
    try:
        res = MeshGeneratorService.generate_3d_model(img_path, MODELS_DIR, slug, style=style)
        row["status"] = "success"
        row["vertices"] = res.get("vertices", 0)
        row["faces"] = res.get("faces", 0)
        row["texture_size"] = res.get("texture_size", "N/A")
        fs = res.get("file_size", "0 MB")
        if isinstance(fs, str):
            row["file_size_mb"] = fs
        else:
            row["file_size_mb"] = f"{fs:.2f} MB"
        row["time_s"] = round(res.get("inference_time", time.time()-t0), 3)
        row["glb_output"] = res.get("glb_path", "")
        row["clip_category"] = "N/A"
        row["clip_confidence"] = 0
        row["template_name"] = "N/A"
        row["similarity"] = 0
    except Exception as e:
        row["status"] = f"error: {str(e)[:100]}"
        row["time_s"] = round(time.time()-t0, 3)
    return row


def main():
    print("="*60)
    print("3DGame Experiment Runner Benchmark")
    print("="*60)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # Init services once
    ts = TemplateService(
        template_dir="static/templates",
        index_path="data/template_index.faiss",
        metadata_db="data/template_metadata.sqlite",
        device=device
    )

    print(f"\nTemplate service available: {ts.is_available()}")
    print(f"Database count: {ts.metadata_db.get_template_count()}")
    print(f"FAISS index: {ts.retrieval.index.ntotal if ts.retrieval.index else 0} vectors")
    print()

    # CSV headers
    HEADERS = [
        "test_name", "expected_category", "method", "status",
        "clip_category", "clip_confidence", "clip_top5",
        "template_name", "template_uid", "similarity", "template_path",
        "vertices", "faces", "texture_size", "file_size_mb",
        "time_s", "glb_output"
    ]

    results = []

    for idx, (name, fname, exp_cat) in enumerate(TEST_IMAGES):
        img_path = os.path.join(IMG_DIR, fname)
        if not os.path.exists(img_path):
            print(f"[{idx+1}/20] SKIP {name}: file not found")
            continue

        img = Image.open(img_path).convert("RGBA")
        slug = f"exp_{name}_{idx}"
        print(f"\n[{idx+1}/20] {name} (expected: {exp_cat})")

        # --- Method 1: Template Retrieval ---
        print(f"  -> template_retrieval ...", end=" ", flush=True)
        r = run_template_method(name, img, img_path, ts, f"{slug}_tpl")
        r["test_name"] = name
        r["expected_category"] = exp_cat
        results.append(r)
        print(f"{r.get('status','?')} ({r.get('time_s',0):.1f}s) sim={r.get('similarity',0):.3f}")

        # --- Method 2: Procedural Elliptical ---
        print(f"  -> procedural_elliptical ...", end=" ", flush=True)
        r2 = run_procedural_method(name, img_path, f"{slug}_ell", "elliptical")
        r2["test_name"] = name
        r2["expected_category"] = exp_cat
        results.append(r2)
        print(f"{r2.get('status','?')} ({r2.get('time_s',0):.1f}s)")

        # --- Method 3: Procedural Extruded ---
        print(f"  -> procedural_extruded ...", end=" ", flush=True)
        r3 = run_procedural_method(name, img_path, f"{slug}_ext", "extruded")
        r3["test_name"] = name
        r3["expected_category"] = exp_cat
        results.append(r3)
        print(f"{r3.get('status','?')} ({r3.get('time_s',0):.1f}s)")

    # Write CSV
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(results)

    # Summary stats
    print(f"\n{'='*60}")
    print(f"Results saved to {OUTPUT}")
    print(f"{'='*60}")

    total = len(results)
    success = sum(1 for r in results if r.get("status") == "success")
    tpl_success = sum(1 for r in results if r.get("method")=="template_retrieval" and r.get("status")=="success")
    ell_success = sum(1 for r in results if r.get("method")=="procedural_elliptical" and r.get("status")=="success")
    ext_success = sum(1 for r in results if r.get("method")=="procedural_extruded" and r.get("status")=="success")

    print(f"\nSummary:")
    print(f"  Total runs: {total}")
    print(f"  Success:    {success}/{total}")
    print(f"  Template:   {tpl_success}/20")
    print(f"  Elliptical: {ell_success}/20")
    print(f"  Extruded:   {ext_success}/20")

    if tpl_success > 0:
        avg_sim = np.mean([r["similarity"] for r in results if r.get("method")=="template_retrieval" and r.get("status")=="success"])
        avg_time = np.mean([r["time_s"] for r in results if r.get("method")=="template_retrieval" and r.get("status")=="success"])
        avg_vert = np.mean([r.get("vertices",0) for r in results if r.get("method")=="template_retrieval" and r.get("status")=="success"])
        print(f"  Avg similarity: {avg_sim:.3f}")
        print(f"  Avg time:       {avg_time:.1f}s")
        print(f"  Avg vertices:   {avg_vert:.0f}")

if __name__ == "__main__":
    main()
