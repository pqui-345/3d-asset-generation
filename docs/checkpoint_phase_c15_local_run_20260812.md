# Checkpoint Pha C1.5 — Chạy local ngày 12/08/2026 (đặc biệt: hạn 22:00, không dùng Colab)

## Tình huống
- Hạn chót giáo viên: 22:00 tối nay. User yêu cầu chạy ngay trên máy local (không Colab).
- Máy: NVIDIA RTX 2050 4GB, torch 2.5.1+cu121, venv `E:\xampp\htdocs\3DGame\venv` (chính là môi trường C1, rembg 2.0.52, open3d 0.19.0).

## Đã xong — TripoSR (benchmark thật, ĐẦY ĐỦ 29/29)
- Chạy: `venv/Scripts/python -m scripts.benchmark.run_local_triposr`
  - Số hiệu: `triposr_local_20260812_045813` (2 lần chạy lỗi đầu do import thiếu, bỏ).
  - run_dir: `experiments/multimodel/raw/triposr_local_20260812_045813/` (meshes/*.glb, run_log.csv, metadata.json).
  - 29/29 success, input_hash check 29/29 PASS, model load 24,6 s.
- Hiệu năng: inference mean ≈ 2,19 s (max 8,6 s vật thể đầu do khởi động), VRAM ≈ 1959 MB,
  n_triangles 76k–590k, tổng ~25 min.
- Eval bằng ĐÚNG evaluator C1 (`experiments/scripts/evaluate_mesh.py`, config standard:
  10k điểm, seed 42, xoay y 8×45°, ICP point-to-point scale=False max_corr 0.05 max_iter 100):
  - kết quả `experiments/multimodel/eval/triposr_local_20260812_045813_eval.csv`, 29/29 OK (~6,5 min).
  - **Tái lập C1 (bằng chứng hợp lệ nhất)**: so với config standard của
    `ablation_eval_ablation_full_20260811.csv` (cùng GPU, cùng giao thức):
    | metric | C1 standard | triposr_local |
    |---|---|---|
    | cd_post_align mean | 0.058955 | 0.059137 (diff +0.0002) |
    | cd_squared_post_align | 0.006694 | 0.006683 |
    | f_tau0.2_post_align | 0.966112 | 0.966502 (diff +0.0004) |
    | f_tau0.5_post_align | 1.000000 | 1.000000 |

## Đang chạy — Hunyuan3D-2mini (batch nền, PID 4656)
- Script: `scripts/benchmark/run_local_hunyuan.py` (fp16 — cấu hình đầy đủ: 30 steps,
  octree 380, num_chunks 20000, output trimesh → GLB, ghi log từng object + resume).
- Smoke (Hefty, cấu hình đầy đủ): box `hunyuan3d2mini_local_20260812_060953`:
  inf 1298 s (~21,6 min/vật thể!), VRAM 4737 MB (tràn shared — giới hạn 4GB).
- Batch: run_id cố định `hunyuan3d2mini_local_run`, 29 vật thể → ETA ~17:00 (nếu không crash).
- Log: `C:\Users\LENOVO\AppData\Local\Temp\opencode\hunyuan_batch.log`.
- Rủi ro: OOM/crash trong batch (VRAM 4737 > 4096 MB) → resume được (log append mỗi object).

## KHÔNG chạy được local — InstantMesh (cần ~14 GB VRAM, máy có 4 GB)
- Kết luận thẳng: không thể chạy local. Các phương án:
  a) Sinh viên chạy Colab T4 (notebook 02 đã sẵn, smoke rồi batch ~1–1,5 h) trong hôm nay hoặc mai;
  b) Nộp report trung thực: 2/3 mô hình có số liệu thật + kế hoạch còn lại.
- KHÔNG bịa số liệu cho InstantMesh.

## Việc còn lại trước 22:00
1. Chờ Hunyuan batch xong → eval 29 mesh (eval_local_meshes.py, ~7 min) → thống kê so sánh 3 dòng.
2. Viết bảng so sánh TripoSR vs Hunyuan3D-2mini (real) + InstantMesh pending (thật) vào báo cáo.
3. merge_and_summarize nếu cần; cập nhật README/guide nếu đổi hướng "local thay Colab".
4. Thông báo cho user 2 bằng chứng tái lập (C1 vs TripoSR local) đề phòng thầy hỏi.

## Xung đột venv (cần theo dõi)
- Cài `hy3dgen 2.0.2` nâng `transformers` lên 5.15.0, `huggingface_hub` 1.27.0, opencv 5.0
  → TripoSR (tsr) không còn được kiểm chứng trong venv này. Nếu phải chạy lại TripoSR
  local → tạo venv riêng (toàn bộ kết quả TripoSR đã có sẵn, không cần chạy lại).