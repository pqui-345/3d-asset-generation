# Báo cáo checkpoint Pha A — Thực nghiệm ablation TripoSR (2026-08-10)

> Theo đúng trình tự đã duyệt: `audit → manifest → evaluator → unit test → ablation config → smoke test → báo cáo`.
> Chưa sửa `main.tex`, chưa điền kết quả nghiên cứu, chưa chạy full Pha B, không tạo số liệu giả, không commit.

## 1. Pha A1 — Không dùng GPU (đã xong)

| Bước | File tạo | Kết quả |
|---|---|---|
| Audit | `docs/experiment_audit_20260810.md` | Môi trường đo thật: Python 3.11.9, torch 2.5.1+cu121, CUDA 12.1, cuDNN 90100, `torch.cuda.is_available()=True`, RTX 2050 (cc 8.6), **VRAM 4095.5 MB**; pipeline preprocessing/inference xác minh từ mã nguồn; chuẩn số liệu (mục 6); khả thi theo VRAM 4 GB (mục 7); ngân sách thời gian; rủi ro; quyết định |
| Xác minh trục (điều kiện 4) | `experiments/scripts/verify_axis_conventions.py` → `experiments/outputs/analysis/axis_verification.{json,csv}` | Silhouette IoU (render perspective đúng camera gốc distance 2.5, mask rembg): **28/29 vật Z-up (96.6%), 0 Y-up, 1 ambiguous** (Orchid pot, IoU thấp cả 2 hướng do mask) → **decision = z_up**; evaluator chuẩn hóa GT Z-up→Y-up (+90°X) để đồng trục với PRED (Y-up đã xác minh từ code), rotation search quanh **Y** |
| Manifest (điều kiện 7) | `experiments/data/manifests/gso30.csv` | 30 hàng (29 usable, 1 excluded: Thomas — thiếu thư mục GSO), 16 cột gồm `geometry_group`, `symmetry_type`, `symmetry_label`, `symmetry_confidence`, `symmetry_reason`, `label_method=ai_assistant_v1`; nhãn gán từ tên vật + kiến thức nội dung, TRƯỚC khi đọc metric; phân bố: rotational 3 / mirror 12 / asymmetric 14 / uncertain 1; symmetric 15 / asymmetric 14 / uncertain 1; không suy luận từ tên file khi không đủ căn cứ (đánh `low`/`uncertain`) |
| Evaluator (điều kiện 3, 4, 5) | `experiments/utils/eval_common.py`, `experiments/scripts/evaluate_mesh.py` | CD Euclidean 2 chiều `0.5*(mean_p min_q ||p-q|| + mean_q min_p ||p-q||)` + CD_fwd/bwd/squared; P/R/F@0.1/0.2/0.5 trong đơn vị **bbox diagonal = 1** (mỗi mesh scale riêng, ghi scale factor); rotation search quanh trục up Y, 8 góc ×45°, chọn CD min; ICP **Open3D point-to-point `scale=False`** ghi đủ: max_correspondence_distance, method, iterations_used, max_iterations, converged (theo dõi inlier_rmse, tol 1e-6), fitness, inlier_rmse, ma trận 4×4 (JSON); metrics pre/post align; bắt lỗi mesh rỗng/NaN/no-face; append CSV + resume (không ghi đè) |
| Unit test (điều kiện 6) | `experiments/tests/test_evaluate_mesh.py` | **15/15 PASS** (pytest 9.1.1, đã cài vào venv): CD=0 & F=1 dùng **cùng point cloud**; CD sphere dịch chuyển = kỳ vọng giải tích (tích phân số) ±0.02; rotation search tìm đúng góc (90/270 cho box 180° đối xứng); ICP nhận diện identity & translation; `pytest.approx` cho align; bắt lỗi rỗng/NaN/no-faces; determinism preprocessing |
| Ablation config (điều kiện 8) | `experiments/configs/ablation.yaml` | 12 dòng cấu hình, **10 input-config độc nhất**; cấu hình chuẩn đối chứng `standard` (rembg + bbox_crop + 512 + ratio 0.85 — khớp pipeline gốc service); các biến giữ cố định khai báo rõ (seed 42, samples 10000, rotation 8×Y, ICP 0.05/100/1e-6, gt_up z→y); `resize_512` và `padding_0.85` khai báo `duplicate_input_of: standard` — dedup bằng input_hash thật |

## 2. Pha A2 — Smoke test trên GPU (đã xong, 24/24 OK)

Lệnh: `venv\Scripts\python.exe experiments\scripts\run_ablation.py --smoke --run-id smoke_test_20260810`
(2 vật: Hefty_Waste_Basket, Jansport_School_Backpack; 12 cấu hình × 2 = **24 dòng kết quả**, **20 inference thật** + 4 dòng reused).

CD post-align (chỉ số chính sau rotation search + ICP):

| Config | Hefty bin (rotational) | Backpack (mirror) |
|---|---|---|
| standard | 0.08255 | 0.05797 |
| without_rembg | 0.07955 | 0.04436 |
| resize_224 | 0.07967 | 0.05980 |
| resize_256 | 0.08114 | 0.06060 |
| resize_384 | 0.08198 | 0.05662 |
| resize_512 (reused) | 0.08255 | 0.05797 |
| resize_768 | 0.08270 | 0.05895 |
| no_tight_crop | 0.08146 | 0.04940 |
| padding_1.00 | 0.08692 | 0.03570 |
| padding_0.90 | 0.08291 | 0.03922 |
| padding_0.85 (reused) | 0.08255 | 0.05797 |
| padding_0.75 | 0.07192 | 0.05477 |

(CD nhỏ hơn = tốt hơn; các số này chỉ là smoke test trên 2 vật, chưa phải kết quả báo cáo.)

## 3. Số liệu vận hành & schema CSV (điều kiện 9)

- **Thời gian trung bình/lượt (bao gồm preprocess + inference + postprocess): 13.58 s** (max 16.5 s; model load riêng 9.9 s/lần chạy).
- **VRAM peak lớn nhất: 1959 MB** (~47% VRAM) — an toàn với RTX 2050 4 GB.
- **Tổng Pha B**: 348 dòng kết quả khai báo (29 vật × 12 cấu hình), **290 inference thật** (10 input unique × 29 vật, 58 dòng reused), dự kiến **≈ 66 phút** (13.58 s × 290) + load model; checkpoint/resume sau mỗi (vật, cấu hình).
- `experiments/logs/ablation_smoke_test_20260810.csv` (24 dòng, 14 cột): run_id, object_id, config, ablation_group, input_hash, reused_from, preprocessing_time_s, inference_time_s, postprocessing_time_s, total_time_s, vram_peak_mb, model_load_time_s, status, error.
- `experiments/outputs/metrics/ablation_eval_smoke_test_20260810.csv` (24 dòng, 53 cột): ROW_FIELDS đầy đủ từ evaluate_mesh (run_id, config, object_id, status, error, gt_axis_normalization, gt/pred_diagonal, gt/pred_scale, samples, seed, rotation_search_*, icp_* gồm icp_transformation JSON, cd_*/f_*/precision_*/recall_* pre/post align, evaluation_time_s) + reused_from.
- 20 file GLB dự đoán: `experiments/outputs/predictions/ablation/smoke_test_20260810/<oid>/<config>.glb` (20 GLB duy nhất — chứng minh dedup hoạt động: resize_512/padding_0.85 không chạy lại).
- `experiments/outputs/metrics/ablation_smoke_test_20260810_summary.json` — tóm tắt tự động.

## 4. Đối chiếu điều kiện

1. ✅ Tách Pha A1 (không GPU) / A2 (GPU) rõ ràng
2. ✅ Audit ghi kết quả CUDA thật (mục 1 audit)
3. ✅ Công thức CD/P/R/F + đơn vị ngưỡng ghi rõ (audit mục 6 + docstring evaluate_mesh.py)
4. ✅ Rotation search quanh Y SAU khi xác minh trục (28/29 z_up) và chuẩn hóa GT→Y-up; không hard-code Z
5. ✅ ICP ghi đủ max_correspondence_distance, method point-to-point, scale=False, ma trận cuối, hội tụ
6. ✅ Test CD=0/F=1 dùng cùng point cloud; align dùng pytest.approx; kỳ vọng CD sphere giải tích
7. ✅ Manifest có geometry_group/symmetry_confidence/symmetry_reason/label_method; nhãn trước metric; uncertain khi thiếu căn cứ
8. ✅ 12 cấu hình, cấu hình chuẩn đối chứng, biến cố định khai báo; dedup input_hash chứng minh bằng 20/24 GLB duy nhất
9. ✅ Checkpoint này: unit test, smoke 24 lượt, schema CSV, thời gian TB, VRAM peak, tổng lượt + dự kiến
10. ✅ Chỉ làm Pha A + smoke; chưa sửa main.tex, chưa điền kết quả, chưa chạy full Pha B

## 5. File tạo mới trong phiên (không ghi đè file cũ)

- docs/experiment_audit_20260810.md
- docs/checkpoint_phase_a_20260810.md (file này)
- experiments/scripts/verify_axis_conventions.py
- experiments/data/manifests/gso30.csv
- experiments/utils/eval_common.py
- experiments/scripts/evaluate_mesh.py
- experiments/tests/test_evaluate_mesh.py
- experiments/configs/ablation.yaml
- experiments/scripts/run_ablation.py
- outputs/analysis/axis_verification.{json,csv}
- logs/ablation_smoke_test_20260810.csv + outputs/metrics/ablation_eval_smoke_test_20260810.csv + summary json
- outputs/predictions/ablation/smoke_test_20260810/ (20 GLB)

## 6. Chờ duyệt trước Pha B

Xin xác nhận để chạy full: `venv\Scripts\python.exe experiments\scripts\run_ablation.py --run-id ablation_full_20260810` (~66 phút GPU liên tục, có checkpoint).
