# Checkpoint Pha B — Ablation TripoSR (2026-08-11)

> File mới, không ghi đè. Dữ liệu ĐÃ qua kiểm tra sau chạy (13 mục, ALL PASS).
> Chưa có nhận xét khoa học nào; thống kê Pha C chưa chạy; chưa sửa `main.tex` / `tailieu.bib`; chưa commit.

## 1. Thông tin chung

| Mục | Giá trị |
|---|---|
| run_id | `ablation_full_20260811` |
| Bắt đầu | 2026-08-11 05:50:55 |
| Kết thúc | 2026-08-11 07:00:07 |
| Tổng thời gian | 4152.4 s (~69.2 phút) |
| Model | TripoSR — `services/weights/model.ckpt` (1,677,246,742 bytes), `config.yaml` (987 bytes) |
| Môi trường | torch 2.5.1+cu121, CUDA 12.1, cuDNN 90100, RTX 2050 (4095.5 MB VRAM) |
| Load model | 8.4 s (1 lần duy nhất) |
| Lệnh chạy | `venv\Scripts\python.exe experiments\scripts\run_ablation.py --run-id ablation_full_20260811` |

## 2. Kết quả định lượng

| Chỉ số | Giá trị |
|---|---|
| Inference thật | **290** (10 cấu hình unique × 29 mẫu) |
| Reused (dedup) | **58** (resize_512, padding_0.85 — mỗi cấu hình 29 dòng) |
| Thành công | **348 / 348** (100%) |
| Thất bại | **0** |
| Số dòng log CSV | 348 |
| Số dòng eval CSV | 348 |
| mean total time | 11.869 s |
| median total time | 11.706 s |
| P95 total time | 14.501 s |
| max total time | 17.243 s |
| Peak VRAM lớn nhất | **1959.3 MB** (an toàn với VRAM 4 GB) |
| Mẫu nhanh nhất (avg) | Schleich_S_Bayala_Unicorn_70432 — 9.74 s |
| Mẫu chậm nhất (avg) | Down_To_Earth_Orchid_Pot_Ceramic_Lime — 14.67 s |
| ETA Pha C còn lại | 0 (toàn bộ 348 dòng đã xong) |

Thời gian ghi tách riêng trong CSV: `preprocessing_time_s`, `inference_time_s`, `postprocessing_time_s`, `total_time_s` (= tổng 3 cột trên), `model_load_time_s`, `evaluation_time_s`.

## 3. Danh sách lỗi

**Không có lỗi nào** — 0 dòng failed, không CUDA OOM, không mesh hỏng, không NaN/Inf, không abort liên tiếp. Dòng failed (nếu có) sẽ có `status=failed`, `success=false`, `error_message`.

## 4. Xử lý mẫu GT ngoại lệ về trục

- **Mẫu**: `Down_To_Earth_Orchid_Pot_Ceramic_Lime` (Orchid pot).
- **Bằng chứng**: silhouette IoU z_up = 0.1983, y_up = 0.1906 → `winner=ambiguous` (cả hai thấp, không phân định được; mask rembg vẫn tốt 17–18% foreground, GT gần khối lập phương 0.140×0.139×0.127).
- **Xử lý** (đúng điều kiện: không ép biến đổi trục chung):
  - Manifest: `axis_verified=False`, `gt_up_axis=ambiguous`, ghi đầy đủ `axis_evidence`.
  - Evaluator: **không áp dụng Z→Y** — `gt_axis_normalization=none_ambiguous_not_validated`, `axis_validated=False` trên cả 12 dòng của mẫu.
  - Inference vẫn chạy đủ 12 cấu hình (290 inference giữ nguyên) vì input không phụ thuộc trục GT.
  - Mẫu này **loại khỏi đánh giá định lượng** ở Pha C (dữ liệu có flag `axis_validated=False` để lọc).
- 28 mẫu còn lại: `gt_up_axis=z`, `axis_validated=True` (xác minh 28/29 = 96.6% z-up, cam chụp +Z đã ghi trong audit).

## 5. Kết quả kiểm tra sau chạy (verify_ablation_run.py — 13/13 PASS)

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | 29 mẫu manifest được xử lý | PASS (29/29, thiếu 0) |
| 2 | Đúng 12 setting trên mỗi mẫu | PASS |
| 3 | Đủ 348 dòng kết quả | PASS (348/348) |
| 4 | Đúng 290 inference thật | PASS (summary khớp 290) |
| 5 | 58 dòng reused, đúng 2 cấu hình trùng, GLB đúng 290 (không dư) | PASS |
| 6 | Không trùng cặp (object_id, setting) | PASS (dups=[]) |
| 7 | Mọi path prediction/input/GT tồn tại | PASS (thiếu 0; reused trỏ về GLB nguồn standard) |
| 8 | Không NaN/Inf | PASS |
| 9 | Dòng thất bại có success=false + error_message | PASS (không có dòng failed) |
| 10 | Mọi dòng có run_id, timestamp, seed=42, model info | PASS |
| 11 | input_hash chứng minh dedup (nhóm standard gồm đúng 3 cấu hình, còn lại hash riêng) | PASS |
| 12 | Orchid pot: gt_up=ambiguous, không áp Z→Y; 28 mẫu khác z_up | PASS |
| 13 | Tái lập evaluator trên 2 prediction đã lưu | PASS — diff = 0.0 (bảng dưới) |

### 5.1 Tái lập evaluator (check 13)

| object_id | config | field | giá trị CSV | chạy lại | sai lệch |
|---|---|---|---|---|---|
| Connect_4_Launchers | resize_768 | cd_post_align | 0.11499057 | 0.11499057 | 0.0 |
| Connect_4_Launchers | resize_768 | f_tau0.2_post_align | 0.692127 | 0.692127 | 0.0 |
| BEDROOM_CLASSIC | resize_256 | cd_post_align | 0.07839541 | 0.07839541 | 0.0 |
| BEDROOM_CLASSIC | resize_256 | f_tau0.2_post_align | 0.890131 | 0.890131 | 0.0 |

(lấy mẫu ngẫu nhiên seed 0 trong các cấu hình có GLB lưu — không lấy dòng reused; sai số cho phép 1e-6)

### 5.2 Tham chiếu nhanh (không phải kết luận khoa học)

- CD post_align cấu hình standard trên 28 mẫu hợp lệ (loại orchid pot): mean = 0.0600, min = 0.0217, max = 0.1242.

## 6. Đường dẫn dữ liệu

| Loại | Đường dẫn |
|---|---|
| Log | `experiments/logs/ablation_ablation_full_20260811.csv` (348 dòng, 22 cột) |
| Metrics | `experiments/outputs/metrics/ablation_eval_ablation_full_20260811.csv` (348 dòng, 61 cột) |
| Summary | `experiments/outputs/metrics/ablation_ablation_full_20260811_summary.json` |
| Verify | `experiments/outputs/metrics/verify_ablation_full_20260811.json` |
| GLB (290) | `experiments/outputs/predictions/ablation/ablation_full_20260811/<object_id>/<config>.glb` |
| Manifest | `experiments/data/manifests/gso30.csv` (20 cột, có gt_up_axis) |
| Checkpoint này | `docs/checkpoint_phase_b_20260811.md` |
| Checkpoint Pha A | `docs/checkpoint_phase_a_20260810.md`, `docs/experiment_audit_20260810.md` |

## 7. Lệnh resume

```powershell
venv\Scripts\python.exe experiments\scripts\run_ablation.py --run-id ablation_full_20260811
```

- Resume tự động: mọi cặp `(run_id, object_id, config)` đã có `status=success` trong eval CSV sẽ **SKIP**, không chạy lại inference.
- Đã kiểm chứng resume trên `smoke_test_v3_20260811`: lần 2 SKIP toàn bộ 24/24, không ghi đè dữ liệu cũ (summary tính lại từ CSV — `log_rows_total=24`, `inferences_run=20`).
- Dòng failed sẽ được chạy lại khi resume.

## 8. Danh sách file tạo/sửa

**Không phải git repo** — thống kê thủ công chính xác:

| Trạng thái | File |
|---|---|
| SỬA | `experiments/data/manifests/gso30.csv` — thêm 4 cột: axis_verified, axis_evidence, gt_up_axis, axis_note |
| SỬA | `experiments/utils/eval_common.py` — `axis_normalize_gt` hỗ trợ `gt_up="ambiguous"` (không chuẩn hóa, ghi `none_ambiguous_not_validated`) |
| SỬA | `experiments/scripts/evaluate_mesh.py` — ROW_FIELDS +7 cột (timestamp, success, error_message, seed, model_weights, model_config, gt_up_axis, axis_validated) và main() điền chúng |
| SỬA | `experiments/scripts/run_ablation.py` — gt_up theo manifest; dedup kiểm tra tham số trùng (RuntimeError nếu lệch); `reused_from_setting`; dòng failed ghi eval row success=false; abort khi ≥3 lỗi liên tiếp; `torch.cuda.synchronize()` trước+sau đo inference; summary tính từ CSV (chống ghi đè khi resume) + resume_command; model load 1 lần |
| TẠO | `experiments/scripts/verify_ablation_run.py` — 13 kiểm tra sau chạy |
| TẠO | `experiments/logs/ablation_ablation_full_20260811.csv` |
| TẠO | `experiments/outputs/metrics/ablation_eval_ablation_full_20260811.csv` |
| TẠO | `experiments/outputs/metrics/ablation_ablation_full_20260811_summary.json` |
| TẠO | `experiments/outputs/metrics/verify_ablation_full_20260811.json` |
| TẠO | `experiments/outputs/predictions/ablation/ablation_full_20260811/` (290 GLB) |
| TẠO (phụ) | `smoke_test_v3_20260811`: log + eval + summary + verify + 20 GLB (dùng kiểm chứng resume/schema) |
| KHÔNG ĐỤNG | `main.tex`, `tailieu.bib`, `services/`, `tsr/`, `docs/experiment_audit.md` (cũ), `experiments/logs/triposr_30.csv` |

## 9. Ghi chú quy trình

- Model load 1 lần; `torch.cuda.reset_peak_memory_stats()` + `empty_cache()` trước từng inference; synchronize trước và sau forward.
- Seed cố định 42; rotation search quanh Y 8 góc; ICP point-to-point scale=False max_corr 0.05, 100 vòng; không thay đổi gì ngoài biến ablation.
- Mọi kết quả checkpoint sau mỗi (object, config), CSV mở/ghi/đóng ngay (flush an toàn).
- **Không tự động sang Pha C** — chờ người dùng duyệt sau khi kiểm tra dữ liệu.
