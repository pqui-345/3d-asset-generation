# Checkpoint Pha C1 — Kiểm tra dữ liệu + thống kê + tài liệu (DỪNG chờ duyệt Pha C2)

Ngày: 2026-08-11 | Run: `ablation_full_20260811` | Script chính: `experiments/scripts/run_stats.py`

## 1. Đã hoàn thành

### 1.1 Kiểm tra dữ liệu — 12/12 PASS [`data_validation.json`]
- c1 348 dòng | c2 29 object_id đúng manifest | c3 mỗi vật thể đủ 12 setting | c4 không trùng khóa
- c5 **290 inference + 58 reused** | c6 290 file .glb | c7 không NaN/Inf | c8 đủ cột flag
- c9 đủ đường dẫn | c10 reused khớp hash + metric nguồn | c11 baseline=[standard] | c12 duplicate_input_of=[resize_512, padding_0.85]

### 1.2 Thống kê [`experiments/results/summary/phase_c1_ablation_full_20260811/`]
| File | Nội dung |
|---|---|
| data_validation.json | 12 kiểm tra, all_pass=true |
| descriptive_statistics.csv | 60 dòng (12 setting × 5 metric), bootstrap seed 42/2000 |
| ablation_statistics.csv | 20 kiểm định: 10 paired (rembg/crop) + 10 RM (resize/padding) |
| posthoc_statistics.csv | 10 cặp Wilcoxon paired + Holm (chỉ resize F@0.2 có omnibus ý nghĩa) |
| symmetry_statistics.csv | 14 vs 14 (Welch/Mann-Whitney/Hedges' g) |
| geometry_statistics.csv | mô tả 3 nhóm + 6 Welch thăm dò có Holm |
| performance_statistics.csv | 10 setting × (pre/inf/post/total, VRAM) — 290 inference thật |
| statistical_analysis.json | toàn bộ số liệu gộp |
| statistical_analysis.md | tường thuật truy vết từng số về CSV/JSON + 11 mục hạn chế |
| figures/ | 12 PNG dpi=200 |

### 1.3 Kết quả chính (tóm tắt — chi tiết trong `statistical_analysis.md`)
- **RemBG: có ảnh hưởng đáng kể sau căn chỉnh** — cd_post_align diff 0.0371, p=5.1e-05, dz=0.91; F@0.1 p=2.3e-05; F@0.2 p=0.0025. Không ảnh hưởng cd_pre_align (p=0.63) → ảnh hưởng chủ yếu lên định hướng/bao hình.
- **Crop bounding-box: không khác** (mọi p ≥ 0.16, effect nhỏ).
- **Resize 224–768: khác yếu ở F@0.2 (Friedman p=0.034, W=0.08) nhưng post-hoc Holm không cặp nào ý nghĩa** (min p_holm=0.2313); CD/F@0.1 không khác.
- **Padding 0.75–1.00: không khác** (p ≥ 0.53, W ≤ 0.02).
- **Symmetry**: pre_align thấy khác (p=0.027, g=−0.87) nhưng **biến mất sau POST_ALIGN** (p=0.88) → không thiên kiến đối xứng với protocol chuẩn.
- **Geometry**: chỉ thăm dò (cylindrical n=5); cd_post_align cyl 0.0816 > box 0.0623 > organic 0.0477; sau Holm không ý nghĩa.
- **Hiệu năng**: success 100%; total trung bình 11.3–13.3 s; VRAM ổn định ~1959 MB; without_rembg tổng lâu hơn (13.3 s) do postprocess thiếu mask.

### 1.4 Tài liệu phục vụ biên tập luận văn (không sửa main.tex/tailieu.bib trong C1)
- `docs/sota_comparison_20260811.md` — bảng công trình gốc (TripoSR, InstantMesh, Wonder3D, Zero123++, CRM, Hunyuan3D 1.0) với nguồn chính thức, số TripoSR GSO xác minh từ arXiv 2403.02151 (CD 0.111, FS@0.1 0.651...), kèm cảnh báo comparability.
- `docs/tailieu_bib_audit_20260811.md` — audit 60 entries: không trùng key/DOI, đủ cite; thiếu 2 entry (Hunyuan3D, CRM); lỗi nhỏ key `chen_survey_2026`.
- `baocao/patch_bibtex_suggestions.bib` — 2 entry đề xuất (không đụng tailieu.bib).
- `experiments/manifests/real_photos.csv` (51 ảnh thật) + `real_photo_evaluation.csv` (765 dòng: 51×3 người×5 tiêu chí) + `real_photo_evaluation_guide.md` (hướng dẫn chấm 1–5).

## 2. Verify cuối — `python experiments/scripts/verify_phase_c1.py` → **ALL PASS (14/14)**
v1 validation 12/12 | v2 đủ 10 file + 12 figures | v3 cấu hình chốt (cd_post_align, n=28, 290, α=0.05, seed 42/2000) | v4 mọi kiểm định n=28 | v5 không NaN/Inf | v6 MD khớp CSV | v7 không khẳng định mạnh | v8 posthoc đúng điều kiện | v9 Holm không giảm p | v10 số nhóm đúng (14/14; 12/5/11) | v11 real photos đủ | v12 docs tồn tại | v13 figures hợp lệ | v14 có báo hạn chế + CI.

## 3. Ranh giới đã giữ
- Không sửa `main.tex`, `tailieu.bib`, manifest, evaluate_mesh.py, eval_common.py.
- Không chạy thêm inference; không commit; không so sánh trực tiếp số với báo cáo gốc; không kết luận "tốt nhất" từ p-value; mọi phát hiện exploratory được gắn nhãn.

## 4. Việc còn lại cho các pha sau
- **Pha C2 (đề xuất)**: chạy classical baselines (SVM/RF/kNN trên HOG hoặc tương đương) — config `classical.yaml`; có thể nối thêm phiếu đánh giá ảnh thật vào báo cáo.
- Biên tập: bổ sung 2 entry BibTeX khi viết chương 2; dùng figures + bảng từ `statistical_analysis.md`.

## 5. Lệnh tái lập
```
python experiments/scripts/run_stats.py
python experiments/scripts/verify_phase_c1.py
```
