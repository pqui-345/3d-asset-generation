# Báo cáo kiểm toán môi trường & thí nghiệm — 2026-08-10 (v2)

> File mới, không thay thế `docs/experiment_audit.md` (2026-07-22, lỗi thời).
> Ghi kết quả đo thực tế tại Pha A, phục vụ 5 nhóm thực nghiệm bổ sung theo yêu cầu giáo viên (Nguyễn Thanh Hải).

---

## 1. Môi trường phần cứng / phần mềm (đo thật 2026-08-10)

Chạy bằng `venv\Scripts\python.exe` (bắt buộc — Python toàn cục chỉ có torch CPU):

| Thành phần | Giá trị đo được |
|---|---|
| Python | 3.11.9 |
| PyTorch | 2.5.1+cu121 |
| `torch.cuda.is_available()` | **True** |
| CUDA build (torch.version.cuda) | 12.1 |
| cuDNN | 90100 |
| GPU | NVIDIA GeForce RTX 2050 (compute capability 8.6) |
| Total VRAM | **4095.5 MB (~4 GB)** |
| Python toàn cục (C:\Users\LENOVO\AppData\Local\Programs\Python\Python311) | torch 2.13.0+cpu (**CPU only**, từng gây lỗi 500) |

Thư viện chính (venv): trimesh 4.12.2, open3d 0.19.0, rembg 2.0.52, scipy 1.15.3, numpy, Pillow.

**Kết luận:** mọi thí nghiệm AI chạy bằng `venv\Scripts\python.exe`; VRAM 4 GB là ràng buộc cứng (mục 7).

## 2. Pipeline preprocessing & inference TripoSR (xác minh từ mã nguồn)

```
ảnh nguồn (RGBA) --> remove_background (rembg)      [tsr/utils.py; bỏ qua nếu có alpha<255]
                  --> resize_foreground(ratio=0.85)  [crop bbox alpha + pad + nền xám 0.5]
                  --> model(image_rgb, device="cuda")
                        image_processor(image, cfg.cond_image_size=512)  [luôn resize 512x512]
                  --> extract_mesh(resolution=256, Marching Cubes)
                  --> Z-up -> Y-up: rotation -90 quanh X   [services/local_tripo_service.py:129-133]
                  --> Screened Poisson (open3d depth=9, cắt density<0.1%, giữ cluster lớn nhất)
```

- `services/weights/config.yaml`: cond_image_size 512; DINOSingleImageTokenizer; Triplane1DTokenizer (plane_size 32, num_channels 1024); Transformer1D 16 lớp; TriplaneUpsampleNetwork; NeRFMLP (120/64/9); TriplaneNeRFRenderer (radius 0.87).
- **Ý nghĩa ablation:** cond_image_size=512 cố định trong model → "độ phân giải nguồn" = độ phân giải ảnh **trước bước chuẩn hóa đầu vào** (224/384/512/768); model luôn nhận 512x512.
- **Kỹ thuật:** `tsr.utils.image_processor` luôn gọi remove_background + resize_foreground(0.85) → ablation resize/crop/padding thực hiện bằng **runtime monkeypatch** `tsr.utils` (KHÔNG sửa file `tsr/`), input_hash trên tensor 512x512 thật để chứng minh đầu vào.

## 3. Quy ước trục tọa độ (rotation search — điều kiện 4)

| Mesh | Trục up | Căn cứ |
|---|---|---|
| Predicted GLB `triposr_30/<id>/<id>.glb` | **Y-up (chắc chắn)** | local_tripo_service.py:129-133 xoay -90X trước khi lưu |
| GT GSO `model.obj`/`model.glb` | **Z-up (ĐÃ XÁC MINH)** | `verify_axis_conventions.py`: silhouette IoU (render perspective đúng camera gốc, distance 2.5) → **28/29 vật z_up (96.6%), 0 y_up, 1 ambiguous** (Down_To_Earth_Orchid_Pot_Ceramic_Lime, IoU 0.198/0.191 — nghi do rembg mask). File: `experiments/outputs/analysis/axis_verification.json/.csv` |

- Heuristic bbox (5 vật) không kết luận được → kiểm chứng bằng **silhouette IoU** trong `verify_axis_conventions.py` (mục 9) trước khi chốt evaluator.
- **Quyết định:** GT (Z-up) và PRED (Y-up) không cùng trục → evaluator chuẩn hóa GT Z-up→Y-up (+90X) cho đồng trục, rotation search quanh **trục up thống nhất (Y)**, 8 góc x 45°, chọn CD min; ghi ma trận chuẩn hóa vào output. Không hard-code trục Z tùy ý.
- **Phát hiện thêm:** `renders/front.png` **hoàn toàn opaque** (alpha=255 mọi pixel dù metadata ghi "transparent") → rembg chạy thật trên cả 29 ảnh; mask phải trích bằng rembg, không dùng alpha.

## 4. Dữ liệu thực nghiệm

- GSO: 300 vật tại `static/templates/gso/`, mỗi vật có model.obj + model.glb + renders/front.png (512x512, camera tại +Z, mesh căn tâm + scale max|v|=1).
- Bộ 30 mẫu (`experiments/logs/triposr_30.csv`): 29 success, 1 failed. **Vật loại:** `Thomas_Friends_Wooden_Railway_Talking_Thomas` (thiếu thư mục GSO — hạng mục bỏ trống, không có mesh).
- 29 dự đoán tại `experiments/outputs/predictions/triposr_30/<id>/`: `<id>.glb` (Y-up, Poisson), `<id>_raw.glb` (Y-up, trước Poisson), `<id>.obj`, preview png.
- 30 mẫu ⊇ 10 mẫu pilot (`triposr_pilot.csv`), bộ pilot có `_raw.glb` phục vụ ablation "raw vs Poisson" (tùy chọn).
- `experiments/data/manifests/gso_all_objects.json`: 1033 mục GSO (thư viện đầy đủ), có license/owner/name — dùng cho cột license trong manifest.

## 5. Kết quả / artifact hiện có (KHÔNG ghi đè)

| File | Nội dung | Ghi chú |
|---|---|---|
| logs/triposr_30.csv | 29 success + 1 fail | inference_time_s, vram_peak_mb, verts, faces, glb_size |
| logs/triposr_pilot.csv | 10 mẫu | pilot |
| outputs/metrics/geometry_metrics_30.json | CD + P/R/F@0.01, n=29 | ICP trimesh (rigid, 100 vòng, 1e-5), 50k mẫu, centroid+scale; **thiếu** rotation search, F@0.1/0.2/0.5, ghi chép hội tụ |
| outputs/metrics/geometry_metrics.json | pilot, không ICP | cũ |
| outputs/metrics/classical_metrics.json | SVM 0.917, RF 0.833 | học máy cổ điển (phân loại) |
| outputs/metrics/resnet18_transfer_metrics.json | 1.0 | |
| outputs/metrics/vit_light_transfer_metrics.json | 0.5/0.25/0.5/0.333 | |
| experiments/logs/triposr_pilot_metrics.json | pilot | |
| outputs/.../ablation_results.csv, multiview_results.csv | phân loại ảnh | không liên quan hình học |
| docs/experiment_audit.md | audit cũ (2026-07-22) | giữ nguyên, không sửa |

Evaluator cũ `run_geometry_metrics.py` / `run_gso_experiment_30.py`: CD unsquared/squared (trimesh), P/R/F@0.01, 50k điểm, ICP trimesh, **không** rotation search, **không** F@0.1/0.2/0.5, không metric trước align, không bắt lỗi hội tụ → **thay bằng evaluator chuẩn mới** (không sửa file cũ).

## 6. Chuẩn số liệu hình học (điều kiện 3)

- **CD (chỉ số chính):** khoảng cách **Euclidean (không bình phương)**, hai chiều:
  `CD = 0.5 * [ mean_{p in P} min_{q in Q} ||p-q||  +  mean_{q in Q} min_{p in P} ||p-q|| ]`
  Ghi kèm CD_forward, CD_backward, CD_squared (phụ).
- **Precision =** % điểm pred có điểm GT cách < τ; **Recall =** % điểm GT có điểm pred cách < τ; **F = 2PR/(P+R)**.
- **Ngưỡng τ = 0.1 / 0.2 / 0.5** tính sau khi chuẩn hóa **bbox diagonal = 1** (mỗi mesh scale riêng, ghi scale factor) — ngưỡng là tỷ lệ của diagonal chuẩn hóa.
- Chuẩn hóa: căn tâm theo centroid, scale theo diagonal; sau đó rotation search (quanh trục up Y, 8 góc) → ICP.

## 7. Khả thi theo VRAM 4 GB

| Nhóm | Đề xuất | Khả thi tại máy? | Phương án |
|---|---|---|---|
| N1 rembg | bật/tắt rembg | **Có** | chạy thật |
| N2 độ phân giải nguồn | 224/384/512/768 | **Có** | chạy thật |
| N3 crop/padding | 2 crop x 4 padding | **Có** | chạy thật (9 input-config độc nhất) |
| N4 đối xứng | nhãn từ manifest | **Có** | phân tích trên dữ liệu chạy thật |
| N5 SOTA so sánh | InstantMesh, CRM, Hunyuan3D, Zero123, Wonder3D | **Không** (InstantMesh ≥8-10 GB, CRM >16 GB, Hunyuan3D ≥10 GB, Zero123 5-7 GB, Wonder3D 4-6 GB) | bảng tổng hợp kết quả công trình gốc công bố (ghi protocol/hardware/source, không xếp hạng chéo) |

## 8. Ngân sách thời gian (ước tính)

- 12 dòng cấu hình khai báo → **10 input-config độc nhất** x 29 vật = **290 lượt inference** (2 dòng trùng input_hash với standard → tái sử dụng, không chạy lại).
- Smoke test 2 vật x 12 cấu hình = 24 dòng kết quả, 20 inference thật → đo thời gian thật/lượt và VRAM peak → ngoại suy tổng thời gian Pha B trong báo cáo checkpoint.

## 9. Các bước Pha A đã/cần làm

1. [x] Audit (file này) — đo CUDA thật, xác minh pipeline, trục, dataset
2. [x] `verify_axis_conventions.py` — **ĐÃ CHẠY**: 28/29 z_up (96.6%), decision=z_up; evaluator chuẩn hóa GT Z-up→Y-up (+90X) rồi rotation search quanh Y
3. [x] `gso30.csv` — **ĐÃ TẠO** `experiments/data/manifests/gso30.csv`: 30 hàng (29 usable), 16 cột (object_id, object_name, category, geometry_group, symmetry_type, symmetry_label, symmetry_confidence, symmetry_reason, label_method=ai_assistant_v1, input_image, ground_truth_mesh, predicted_mesh, source_dataset, license_or_source, usable, exclusion_reason); nhãn gán từ tên vật + kiến thức nội dung trước khi đọc metric: symmetric 15 / asymmetric 14 / uncertain 1; rotational 3, mirror 12, asymmetric 14
4. [x] `evaluate_mesh.py` + `eval_common.py` — **ĐÃ TẠO**: CD Euclidean 2 chiều, F@0.1/0.2/0.5 (đơn vị diagonal=1), rotation search quanh Y 8 góc, ICP Open3D point-to-point scale=False (ghi max_correspondence_distance, ma trận 4×4, fitness, inlier_rmse, iterations, converged), metrics pre/post align, batch lỗi mesh rỗng/NaN, append CSV + resume (không ghi đè)
5. [x] `test_evaluate_mesh.py` — **ĐÃ CHẠY: 15/15 PASS** (cùng point cloud → CD=0/F=1; CD sphere dịch = kỳ vọng giải tích; rotation search tìm đúng góc; ICP nhận dạng; bắt lỗi rỗng/NaN/no-faces; determinism preprocessing)
6. [x] `ablation.yaml` — **ĐÃ TẠO** `experiments/configs/ablation.yaml`: 12 dòng (10 unique input, resize_512/padding_0.85 đánh dấu duplicate_input_of: standard), standard = đối chứng, biến cố định khai báo
7. [x] Smoke test 2 vật × 12 cấu hình (GPU) — **ĐÃ CHẠY 24/24 OK**: 20 inference thật + 4 reused; avg 13.58 s/lượt; VRAM peak 1959 MB; ETA Pha B ≈ 66 phút (290 inference) — xem `docs/checkpoint_phase_a_20260810.md`
8. [ ] (Pha B — sau khi user duyệt) full 290 inference, run_stats.py, bảng SOTA, tailieu.bib, main.tex

## 10. Rủi ro

- VRAM 4 GB: chunk_size renderer 8192 đã cấu hình; smoke test đo peak thật.
- rembg trên ảnh opaque: đã chạy thành công ở bộ 30 cũ (29/29), nhưng `without_rembg` cần kiểm tra chất lượng.
- ICP không hội tụ: evaluator bắt lỗi, ghi trạng thái, không dừng toàn bộ.
- Rotation search chỉ quanh trục up: nếu GT nghiêng >45 so với trục chuẩn, CD cao — ghi nhận trong phân tích đối xứng.
- Không có git: mọi thay đổi được backup thủ công; không commit.

## 11. Quyết định đã ghi nhận (phiên 2026-08-10)

- Audit tạo file mới (không ghi đè file cũ); GPU chạy liên tục Pha B sau khi có checkpoint; ảnh thật chỉ tạo schema + runbook (không tạo ảnh giả); nhãn đối xứng do AI gán (uncertain loại khỏi kiểm định chính); không sửa main.tex cho tới khi có số liệu thật; không tạo số liệu giả; không commit.
