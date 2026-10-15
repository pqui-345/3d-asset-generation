# Checkpoint Pha C2 — Viết lại Chương 4 theo kết quả C1 + đồng bộ số liệu toàn báo cáo

Ngày: 2026-08-11 | Tệp biên tập: `baocao/main.tex` (1710 → 1897 dòng) | PDF: `baocao/main.pdf` (80 trang, ~11,5 MB, MiKTeX 25.12)

## 1. Đã hoàn thành

### 1.1 Chương 4 viết lại hoàn toàn (thay Chương 4 số pilot cũ, 46.780 ký tự đã cắt)
- Thứ tự mục chốt (đối chiếu `main.toc`): 4.1 Giới thiệu → 4.2 Môi trường (`tab:environment-c1`) → 4.3 Dữ liệu/thiết kế (`tab:settings`) → 4.4 Giao thức (`eq:cd-c1`, `eq:pr-c1`, `eq:fscore-c1`; chuẩn hóa trục z-up→y-up, bbox=1, rotation search 8×45°, ICP point-to-point max_corr_dist 0,05/max 100 vòng/tol 1e-6; 10K điểm; τ=0,1/0,2/0,5; Friedman+Holm, α=0,05) → 4.5 `tab:descriptive` → 4.6 Ablation (4.6.1 RemBG `tab:rembg-results`+`fig:rembg`; 4.6.2 Crop; 4.6.3 Resize `tab:posthoc`+`fig:resize`; 4.6.4 Padding) → 4.7 Thăm dò (đối xứng `fig:symmetry`; hình học `tab:geometry`+`fig:geometry`) → 4.8 Hiệu năng `tab:performance` → 4.9 SOTA `tab:sota` → 4.10 Ca điển hình/định tính (khôi phục từ backup: `fig:comparisons`, `fig:visual-comparisons`, `fig:ui-thu-vien`, `fig:ui-game-demo`) → 4.11 Đánh giá chức năng web (`sec:walkthrough`, 5 ảnh UI, `fig:multiview-dog`) → 4.12 Hạn chế/thảo luận (`fig:gso-samples`) → 4.13 Ảnh thật (chỉ thiết kế, chưa có điểm) → 4.14 Tóm tắt chương.
- Cơ chế biên tập: cắt bằng marker + placeholder `CHUONG4_P1..P10` + 10 edit nhỏ; không còn marker sót.

### 1.2 Số liệu chính thức C1 đã khớp (nguồn duy nhất `experiments/results/summary/phase_c1_ablation_full_20260811/` + log `experiments/logs/ablation_ablation_full_20260811.csv`)
- 29 vật thể / 12 cấu hình / 348 lượt (290 inference + 58 reused); 100%; inf trung bình 2,243 s (trung vị 2,189; p95 2,304; max 4,017 outlier); total 11,906 (11,563; p95 14,737); pre 1,54 / post 8,12; VRAM 1959,2 MB; cold start 8,4 s (model_load_time_s).
- CD post-align 0,0600 (trung vị 0,0535; CI95 [0,0501; 0,0706]), n=28; F@0,1/0,2/0,5 = 0,796/0,965/1,000 (bão hòa).
- RemBG: CD −0,0371 (p=5,1e-05), F@0,1 +0,2535 (p=2,3e-05); pre-align p=0,63. Crop/resize/padding không ý nghĩa sau Holm (min p_holm 0,2313).
- Symmetry: pre p=0,0268 → post p=0,88. Geometry: cyl 0,0816 / box 0,0623 / organic 0,0477 (thăm dò).
- SOTA (xác minh `docs/sota_comparison_20260811.md`): TripoSR CD 0,111/FS@0,1 0,651/FS@0,2 0,871; One-2-3-45 0,227/0,382/0,630; ZeroShape 0,160/0,489/0,757; TGS 0,122/0,637/0,846; OpenLRM 0,180/0,430/0,698; InstantMesh ~10 s A100; CRM ~10 s A800; Wonder3D optimization; Hunyuan3D lite ≈10 s / standard ≈25 s. Kèm cảnh báo không so sánh công bằng.

### 1.3 Đồng bộ số pilot lệch còn sót (toàn báo cáo)
- Tóm tắt: 29/348/100%/~2,2 s/~12 s (p95 14,7)/1959 MB/0,0600/F@0,1 0,796/F@0,2 0,965/rembg 0,0371 p=5,1e-05; "15–30 giây" → "≈12 giây".
- Chương 2: TripoSR 0,107/86,10% → 0,111/F@0,1 65,1% (2 bảng + 1 mô tả).
- Chương 3: 29 vật thể (loại Orchid, n=28), "348 lượt (29×12)", cold start 8,4 s + VRAM 1959 MB (Bảng 4.7), inference "vài giây–hơn 20 giây (≈2,2 s C1)".
- Chương 5: items, `tab:summary-results` (thay toàn bộ), mục tiêu, RQ1–RQ4 (RQ3 theo ablation C1), hạn chế (10K, τ∈{0,1;0,2;0,5}, F@0,5 bão hòa), kết đoạn 0,0600, hướng phát triển.
- Số pilot 0,3453/0,0483/τ=0,01/50K GIỮ có chủ đích (gắn nhãn "pilot cũ") ở: 4.5, 4.10, 4.11.3, 4.12.4, dung lượng GLB 3,87 MB (nhãn pilot 30 mẫu).

### 1.4 Phụ lục mới (A/B/C, đánh số đúng trong toc)
- **A. TÁI LẬP THỰC NGHIỆM**: bảng phiên bản phần mềm (`analysis_config.json`: python 3.11.9, numpy 2.4.6, scipy 1.15.3, matplotlib 3.11.1, torch 2.13.0+cpu; inference torch 2.5.1+cu121/CUDA 12.1; rembg 2.0.52 u2net; TripoSR ckpt 1.677.246.742 bytes); bảng 4 bước tái lập (run_ablation.py → evaluate_mesh.py/verify_ablation_run.py/verify_phase_c1.py → run_stats.py → make_tables_figures.py); bảng ánh xạ tệp CSV → bảng/hình báo cáo; hướng dẫn chấm ảnh thật (guide + schema 8 cột, chưa có điểm); cách biên dịch LaTeX (pdflatex→bibtex→pdflatex×2).
- **B. DANH SÁCH MẪU VÀ ÁNH XẠ CẤU HÌNH**: manifest gso30.csv = 30 vật thể, 29 usable; Thomas_Friends loại (missing_gso_directory), Orchid pot chạy nhưng loại khỏi hình học (n=28); bảng 12 cấu hình + ghi rõ 2 cấu hình reused.
- **C. CÁC TRƯỜNG DỮ LIỆU ĐÁNH GIÁ**: bảng cột tệp log (23 cột) + bảng cột tệp độ đo (nhóm: nhận dạng, chuẩn hóa trục, lấy mẫu 10000, rotation search, ICP, CD/F-score theo τ, reused) — giá trị ví dụ BAGEL_WITH_CHEESE standard.

### 1.5 Chất lượng biên dịch
- 3 pass pdflatex OK, 80 trang; `bibtex` 0 warning (60 keys phân giải, gồm `xu_instantmesh_2024`, `long_wonder3d_2023`, `liu_one2345_2023`); không undefined reference/citation; không label trùng (đã đổi `tab:environment-c1` khỏi trùng chương 3).
- Overfull còn lại ≤ 36 pt (chủ yếu toc chương 2, danh mục chương 3 — tồn tại từ trước); các tệp đường dẫn trong văn bản dùng `\slash` + `\_\allowbreak` (lưu ý: KHÔNG thêm khoảng trắng sau `\allowbreak` — TeX nuốt khoảng trắng sau control word).
- Hình: 6 PNG C1 đã copy vào `report_images/` (c1_cd_rembg, c1_f_rembg, c1_cd_resize, c1_f_resize, c1_symmetry, c1_geometry); mọi `\includegraphics` giải quyết được (halt-on-error qua 3 pass).

## 2. Ranh giới đã giữ
- Không chạy lại inference; không sửa dữ liệu Pha B/C1/manifest/eval scripts; không commit/push (thư mục không phải git repo — đã kiểm tra).
- Không tạo điểm ảnh thật giả: mục 4.13 + Phụ lục A.5 ghi rõ "chưa có kết quả", score để trống.
- Không so sánh trực tiếp số C1 với số công trình gốc (cảnh báo comparability ở 4.9).

## 3. Việc còn lại (không chặn nộp)
- Kiểm tra trực quan trang PDF (bảng/figures) trước khi nộp — chưa làm được trong phiên này.
- Overfull 36 pt ở danh mục bảng chương 3 (mục 3.6) và toc chương 2 là tiền tồn tại — có thể chỉnh nếu muốn sạch tuyệt đối.
- Git diff không chạy được (không có repo git).

## 4. Lệnh tái lập
```
pdflatex main.tex; bibtex main; pdflatex main.tex; pdflatex main.tex   (thư mục baocao/)
```
