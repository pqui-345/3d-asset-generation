# Experiment Audit — Khảo sát repository trước khi thực nghiệm

> Ngày tạo: 2026-07-22  
> Mục đích: Đáp ứng Giai đoạn 0 của `PROMPT_OPENCODE_THUC_NGHIEM.md`.  
> Chưa sửa code. Chưa tạo file thực nghiệm. Chỉ khảo sát và báo cáo.

---

## 1. Tổng quan repository

- **Đường dẫn:** `E:\xampp\htdocs\3DGame`
- **Git:** KHÔNG phải git repository (không có `.git/`). Không thể `git status` / `git stash`. Mọi thay đổi cần sao lưu thủ công.
- **Loại:** Web demo (Flask SPA), pipeline inference-only, không phải Unity/game.
- **Python venv:** `venv/` có sẵn, torch 2.5.1+cu121 đã cài nhưng **CUDA không khả dụng** trong process này (`torch.cuda.is_available() == False`).

### Phần cứng xác nhận bằng lệnh thực tế

| thành phần | giá trị | nguồn |
|---|---|---|
| CPU | 12th Gen Intel Core i5-12450HX, 8 physical cores / 12 logical | `Get-CimInstance Win32_Processor` |
| RAM total | 16,092 MB | `Win32_OperatingSystem` |
| RAM free lúc đo | ~2,398 MB (đang dùng nhiều) | `Win32_OperatingSystem` |
| GPU | NVIDIA RTX 2050 (theo spec user; `nvidia-smi` cần admin, không chạy được trong shell này) | spec |
| CUDA (torch) | **False** trong process này — có thể do shell không thấy GPU hoặc driver mismatch | `torch.cuda.is_available()` |
| VRAM | 4 GB (theo spec user) | spec |

> **Cảnh báo quan trọng:** `torch.cuda.is_available()` trả `False` trong session测量 này. Nếu GPU thực sự có nhưng shell không thấy, cần chạy lại với quyền admin hoặc kiểm tra `nvidia-smi` ngoài terminal. Ngân sách GPU cho thực nghiệm phụ thuộc việc này — đã đưa vào nhóm câu hỏi.

### Thư viện đã cài trong venv (xác nhận import thành công)

| gói | phiên bản | trạng thái |
|---|---|---|
| torch | 2.5.1+cu121 | OK (CPU mode) |
| torchvision | 0.20.1+cu121 | OK |
| trimesh | 4.12.2 | OK |
| open3d | 0.19.0 | OK |
| scipy | 1.15.3 | OK |
| opencv-python | 4.11.0 | OK |
| faiss-cpu | 1.14.3 | OK |
| clip (OpenAI) | OK | OK |
| rembg | 2.0.52 | OK |
| **scikit-learn** | **THIẾU** | cần `pip install scikit-learn` cho HOG–SVM/RF |
| Flask, PyMySQL, Pillow, numpy | OK | OK |

---

## 2. Cấu trúc mã nguồn (rút gọn, chỉ phần liên quan thực nghiệm)

```
3DGame/
├── app.py                         # Flask entry point
├── routes/
│   ├── main_routes.py             # render index.html (SPA)
│   └── api_routes.py              # 9 API endpoints (xem §4)
├── services/
│   ├── bg_remover.py              # rembg u2net (mặc định, không chỉ định model)
│   ├── db_service.py              # MySQL/SQLite fallback, table `assets` (15+1 cột)
│   ├── local_tripo_service.py     # **TripoSR offline GPU** — chỉ dùng image_paths[0]
│   ├── template_service.py        # CLIP retrieval + Laplacian deformation
│   ├── recognition_service.py     # CLIP ViT-B/32 category + embedding
│   ├── retrieval_service.py       # FAISS search
│   ├── deformation_service.py     # scipy.sparse Laplacian
│   ├── texture_transfer_service.py
│   ├── mesh_generator.py          # **LEGACY DISABLED** (procedural elliptical/relief)
│   ├── tripo_service.py           # cloud API (Tripo AI, HF Space)
│   └── weights/
│       ├── model.ckpt             # 1,599.5 MB — TripoSR checkpoint ✓ TỒN TẠI
│       └── config.yaml             # 987 bytes ✓ TỒN TẠI
├── TripoSR/                        # upstream TripoSR repo (tsr/ package, examples/)
│   └── examples/                  # 14 ảnh paper (chair, flamingo, hamburger, ...)
├── static/
│   ├── uploads/                   # ảnh người dùng (gitignored)
│   └── models/                    # GLB/OBJ/PLY output (gitignored)
├── data/                           # **không phải dữ liệu thực nghiệm**
│   ├── template_metadata.sqlite   # 13.7 MB — metadata 376 template Objaverse
│   ├── template_index.faiss       # 5.7 MB — vector index
│   └── template_index_metadata.json # manifest id→view→glb
├── static/templates/
│   ├── core_100/                  # 101 GLB template (Objaverse subset)
│   └── objaverse_ext/             # 376 GLB template mở rộng
├── scripts/                        # 15 scripts (xem §5)
├── docs/                           # 11 files báo cáo có sẵn
├── 3dgame.db                       # SQLite fallback DB
├── Du_Lieu_Nghien_Cuu.xlsx         # bảng số liệu cũ (chưa audit)
└── 3DGS_Training_Notebook.ipynb   # notebook 3DGS (không liên quan TripoSR)
```

---

## 3. Code path TripoSR — xác nhận chỉ dùng ảnh Front/MAIN

Đây là kết luận quan trọng nhất của audit.

### Chuỗi gọi

1. `routes/api_routes.py` `/api/generate-3d` (line 185–193):
   ```python
   all_image_paths = [no_bg_abs_path] + additional_abs   # list tất cả ảnh no-bg
   results = lts.generate_3d(all_image_paths, models_dir, asset_slug)
   ```
   → Truyền **list tất cả ảnh**, không phải 1 ảnh.

2. `services/local_tripo_service.py` `generate_3d(image_paths, ...)` (line 56, 93–114):
   ```python
   primary_path = image_paths[0]          # CHỈ lấy phần tử đầu = Front/MAIN
   img = Image.open(primary_path)
   img_nobg = remove_background(img)
   img_processed = resize_foreground(img_nobg, 0.85)
   ...
   scene = self.model(img_rgb, device="cuda")   # TSR thấy MỘT ảnh duy nhất
   ```

### Kết luận

- **TripoSR chỉ nhận 1 ảnh** (Front/MAIN = `image_paths[0]`).
- Ảnh left/right/back/top/bottom **KHÔNG** được fusion hình học. Chúng chỉ đếm vào metadata `uploaded_image_count`.
- `model_fusion_image_count` hard-code = 1 (line ~248).
- `used_views = ["front"]`, `ignored_views = ["back","left","right",...][:N-1]`.
- **Không được tuyên bố hệ thống multi-view reconstruction.**

### Lưu ý thêm

- `local_tripo_service.py` chạy **FP32** thực tế (dù docstring ghi FP16). `_load_model()` không có `.half()`.
- `inference_time` bao gồm cả cold-load checkpoint (lần đầu) và inference — chưa tách cold-start vs warm-run.
- Output: GLB ✓, OBJ ✓, **PLY ✗** (trả `ply_path = ""`).

---

## 4. API endpoints (9 routes)

| # | route | method | mục đích | lưu |
|---|---|---|---|---|
| 1 | `/api/upload` | POST | Lưu nhiều ảnh, ảnh đầu = primary | `original_image`, `additional_images` (JSON) |
| 2 | `/api/bg-remove` | POST | rembg trên primary + additional | ghi đè `additional_images` bằng đường dẫn no-bg |
| 3 | `/api/generate-3d` | POST | dispatch TripoSR / template_retrieval | `model_glb/obj/ply`, `vertices`, `faces`, `inference_time` |
| 4 | `/api/assets` | GET | list asset | — |
| 5 | `/api/assets/<id>` | GET | 1 asset | — |
| 6 | `/api/assets/<id>` | DELETE | xóa file + DB row | — |
| 7 | `/api/assets/<id>/editor-save` | POST | lưu editor JSON | `assets.editor_state` (cột ALTER thêm) |
| 8 | `/api/assets/<id>/editor-load` | GET | trả editor JSON | — |
| 9 | `/api/assets/<id>/export-edited` | POST | base64 GLB → ghi `*_edited.glb` | cập nhật `model_glb` |

### Bảng `assets` (16 cột hiệu lực)

`id, name, original_image, additional_images, no_bg_image, model_glb, model_obj, model_ply, vertices, faces, texture_size, file_size, inference_time, style, created_at, editor_state`

- `style` lưu `'template_retrieval'` hoặc `'local_triposr_gpu'` (chọn từ UI).
- Không có cột `method` riêng — `style` đóng vai trò method.
- Không có cột VRAM, raw_vertex_count, foreground_ratio — các giá trị này chỉ trả về trong JSON response, không lưu DB.

---

## 5. Scripts hiện có (15 files trong `scripts/`)

| file | mục đích (1 dòng) | trạng thái |
|---|---|---|
| `run_experiments.py` | benchmark 20 ảnh qua pipeline retrieval | working (harness) |
| `download_gso.py` | tải subset Google Scanned Objects vào template DB | prototype |
| `expand_and_render.py` | mở rộng Objaverse lên 500+, render 6 view 512px | prototype |
| `render_core_views.py` | render 6 view cho `core_100` + update FAISS | working |
| `build_template_db.py` | build 100 template Objaverse (v1) | working |
| `build_template_db_v2.py` | build template DB v2 (error handling tốt hơn) | working |
| `benchmark_templates.py` | benchmark template retrieval với dummy asset | prototype |
| `test_pipeline.py` | smoke test pipeline retrieval (synthetic chair) | working |
| `test_retrieval.py` | test FAISS lookup + self-match sanity | working |
| `test_high_sim.py` | test high-similarity match với template gốc | prototype |
| `test_annotations.py` | check Objaverse annotations + EDU_KEYWORDS | working |
| `test_curator.py` | prototype early curation (core_100) | prototype |
| `debug_retrieval.py` | debug RecognitionService + RetrievalService | working |
| `generate_2d_demo.py` | render multiview demo từ mesh | prototype |
| `_generate_test_inputs.py` | tạo 20 PNG test cho benchmark | working |

**Đặc điểm chung:** tất cả `os.chdir('E:\\xampp\\htdocs\\3DGame')` hard-code, dùng CLIP+FAISS+trimesh+SQLite, render 6 view 512px. Không có script HOG–SVM/RF, ResNet-18, ViT, augmentation A0/A1/A2, B0/B1, Chamfer Distance, F-score.

---

## 6. Dữ liệu thực nghiệm hiện có / thiếu

| mục | có/không | vị trí | ghi chú |
|---|---|---|---|
| TripoSR checkpoint | CÓ | `services/weights/model.ckpt` (1.6 GB) | FP32 inference |
| TripoSR `config.yaml` | CÓ | `services/weights/config.yaml` | |
| TripoSR paper examples | CÓ | `TripoSR/examples/` (14 ảnh) | chair, flamingo, hamburger, ... |
| Template catalog | CÓ | `static/templates/objaverse_ext/` (376 GLB) | dùng cho retrieval, không phải ground-truth |
| Template FAISS index | CÓ | `data/template_index.faiss` | |
| Template SQLite metadata | CÓ | `data/template_metadata.sqlite` | |
| **experiments/ directory** | **KHÔNG** | — | cần tạo mới |
| **Dataset manifest CSV** | **KHÔNG** | — | chưa có `dataset_manifest.csv` |
| **Split file** | **KHÔNG** | — | chưa có `split_summary.csv` |
| **ShapeNet dataset** | **KHÔNG** | — | không có trên disk trong/ngoài 3DGame (đã scan depth 3) |
| **GSO dataset** | **KHÔNG** | — | chỉ có script `download_gso.py`, chưa chạy |
| **Ảnh tự chụp** | **KHÔNG** (từ góc thực nghiệm) | `static/uploads/` chỉ có ảnh demo người dùng | chưa có bộ ảnh tự chụp có nhãn |
| **YAML config thực nghiệm** | **KHÔNG** | — | chỉ có `services/weights/config.yaml` (model arch, không phải experiment config) |
| `scikit-learn` (HOG-SVM/RF) | **KHÔNG cài** | — | cần `pip install scikit-learn` |
| ResNet-18 / ViT pretrained | **CHƯA kiểm tra** | — | torchvision có sẵn ResNet-18; ViT cần chọn checkpoint |
| 3DGS notebook | CÓ | `3DGS_Training_Notebook.ipynb` | không liên quan TripoSR, có thể bỏ qua |
| `Du_Lieu_Nghien_Cuu.xlsx` | CÓ | root | bảng số liệu cũ, cần audit nội dung trước khi dùng |

---

## 7. Chức năng đã có / chưa có / lỗi / chỉ UI

### Đã có và hoạt động thật (backend thật)

- Upload nhiều ảnh → lưu disk + DB.
- `rembg` tách nền (model u2net mặc định), PIL fallback nếu thiếu rembg.
- TripoSR offline inference (FP32, checkpoint `model.ckpt`, chỉ ảnh Front/MAIN).
- Template retrieval: CLIP embedding → FAISS search → Laplacian deformation → texture transfer.
- GLB/OBJ/PLY export (TripoSR: GLB+OBJ; template: GLB+OBJ+PLY; procedural: GLB+OBJ+PLY+MTL).
- Three.js viewer: GLTFLoader, OrbitControls, TransformControls, camera presets, gizmo, editor panel.
- AssetEditor: transform (gizmo + slider), material (color/metallic/roughness), sticker, undo/redo, save/load editor_state, export edited GLB.
- Library: list, search, sort, delete (DB + file).
- DB: MySQL XAMPP + SQLite fallback (16 cột `assets`).

### Chỉ có UI / xử lý chưa thật

- "Ảnh góc bổ sung" (left/right/back/top/bottom): UI cho upload nhiều ảnh, backend lưu + rembg, nhưng **TripoSR không dùng** (chỉ metadata). Không nên tuyên bố multi-view.
- `mesh_generator.py` (procedural elliptical/relief 2.5D): **đã bị loại khỏi routing** (xem `docs/simplify_generation_methods_report.md`). Code còn trong `services/` nhưng không được gọi.
- `tripo_service.py` (cloud API Tripo AI / HF Space): có code nhưng cần API key/network, không chạy offline.

### Lỗi/thiếu cần lưu ý thực nghiệm

- **CUDA không khả dụng** trong session này (`torch.cuda.is_available() == False`). Nếu GPU thật sự có, cần shell admin hoặc kiểm tra driver. Ngân sách TripoSR GPU phụ thuộc.
- **`scikit-learn` chưa cài** → HOG–SVM/RF không chạy được cho đến khi `pip install scikit-learn`.
- **Không có experiments/ scaffolding** → cần tạo toàn bộ cấu trúc Giai đoạn 1.
- **Không có dataset manifest** → Giai đoạn 2 phải tạo từ.ShapeNet/GSO/ảnh tự chụp.
- **TripoSR `inference_time` trộn cold-start + warm-run** → cần đo riêng để công bằng.
- **TripoSR output PLY rỗng** → nếu bảng system performance report PLY bytes, phải ghi `--` chứ không ghi 0.
- **rembg không chỉ định model** (dùng default u2net) → nếu muốn B1 ablation dùng `isnet-general-use` hoặc `u2netp`, cần chỉ định tham số.
- **Không có Git** → không thể `git stash`/rollback. Mọi file mới nên đặt trong `experiments/` và `docs/`, không sửa file service/route hiện có trừ khi thật sự cần.

### Item overhaul rủi ro

- Không sửa `services/local_tripo_service.py`, `routes/api_routes.py`, `services/bg_remover.py`, `services/db_service.py` trong Giai đoạn 0. Mọi instrument nên làm qua wrapper script gọi các service có sẵn, không chèn code vào service gốc (trừ khi tôi xác nhận).
- Web demo phải vẫn chạy được: `python app.py` → `http://127.0.0.1:5000` → upload → generate → viewer → editor → export. Không phá vỡ.

---

## 8. Kế hoạch file sẽ tạo/sửa (dự kiến, chờ xác nhận)

### Giai đoạn 1 — scaffolding (chỉ tạo mới, không sửa code cũ)

```
experiments/
├── README.md
├── configs/
│   ├── classical.yaml
│   ├── resnet18.yaml
│   ├── vit_light.yaml
│   ├── augmentation_a0.yaml
│   ├── augmentation_a1.yaml
│   ├── augmentation_a2.yaml
│   └── triposr_eval.yaml
├── data/manifests/        # dataset_manifest.csv, split_summary.csv
├── scripts/               # run_classical.py, run_deep.py, run_augmentation.py,
│                          # run_background.py, run_triposr_eval.py, make_tables_figures.py
├── outputs/
│   ├── logs/
│   ├── metrics/
│   ├── predictions/
│   ├── figures/
│   └── tables/
└── utils/                  # common.py (seed, config loader, git commit, GPU info)
```

**Không sửa:** `app.py`, `routes/`, `services/`, `templates/`, `static/`, `scripts/` (cũ).  
**Có thể sửa:** `requirements-advanced.txt` (thêm `scikit-learn`, ViT checkpoint) — chỉ khi tôi xác nhận.

### Giai đoạn 2–7

- Tạo manifest/split dựa trên dataset tôi xác nhận (ShapeNet 5 lớp / GSO / ảnh tự chụp).
- Viết script đọc config YAML, gọi service có sẵn (hoặc copy logic) không sửa service gốc.
- Script TripoSR eval: gọi `LocalTripoService` qua wrapper, đo cold/warm riêng, log VRAM qua `torch.cuda.memory_allocated`.
- Không tự điền số liệu vào `main.tex`; sinh fragment `experiments/outputs/tables/*.tex`.

### Báo cáo

- `docs/experiment_audit.md` (file này)
- `docs/experiment_final_report.md` (Giai đoạn 7)
- `docs/how_to_reproduce_experiments.md` (Giai đoạn 7)
- `docs/latex_evidence_map.md` (Giai đoạn 7)

---

## 9. Nhóm câu hỏi duy nhất (trả lời trước khi sang Giai đoạn 1)

Tôi chỉ hỏi một lần theo yêu cầu. Vui lòng trả lời nhóm dưới đây.

### Câu hỏi 1 — ShapeNet 5 lớp

Prompt yêu cầu "năm lớp tôi xác nhận" nhưng tôi chưa biết bạn chọn lớp nào. ShapeNet không có sẵn trên disk (phải tải ~30+ GB nếu lấy ShapeNetCoreV2).

- **A.** Bạn chọn 5 lớp nào? (gợi ý giáo dục: `chair, table, lamp, cup, bottle` hoặc `airplane, car, chair, lamp, guitar` — bạn quyết).
- **B.** Tôi có được tải ShapeNet không? Nếu có, dùng ShapeNetCoreV2 (canonical) hay 3D-R2N2 render (đã có sẵn split official)?
- **C.** Nếu không tải được do dung lượng, có dùng render 2D từ template Objaverse hiện có (376 GLB) làm surrogate classification dataset không? (ghi rõ trong báo cáo là surrogate, không phải ShapeNet).

### Câu hỏi 2 — GSO

- **A.** Số mẫu GSO cần? (paper TripoSR dùng ~300; bạn có muốn subset nhỏ hơn, ví dụ 30 hoặc 50, cho phù hợp ngân sách?)
- **B.** Script `scripts/download_gso.py` đã có — tôi chạy nó và chọn top-N theo ID, hay bạn có danh sách ID cụ thể?
- **C.** Có ground-truth mesh cho GSO không? (GSO gốc có mesh scan, nhưng download có thể chỉ là ảnh — cần xác nhận before tính CD/F-score.)

### Câu hỏi 3 — Ảnh tự chụp

- **A.** Bạn có sẵn bộ ảnh tự chụp đúng không? Nếu có, đường dẫn thư mục và số lượng?
- **B.** Điều kiện chụp: nền đơn/trùng lặp, ánh sáng trong nhà, góc nào (front only hay front+left+right)?
- **C.** Có vật thể đối chiếu ground-truth không (để tính CD/F-score), hay chỉ dùng để demo qualitative?

### Câu hỏi 4 — Ngân sách chạy

- **A.** GPU có thực sự khả dụng không? Session này `torch.cuda.is_available() == False`. Nếu cần GPU, bạn có thể chạy `nvidia-smi` ngoài PowerShell admin và gửi kết quả, hoặc bạn muốn tôi downscale TripoSR eval sang CPU (rất chậm, ~60–120s/sample) với giới hạn mẫu nhỏ (10–20)?
- **B.** Thời gian tối đa bạn cho phép chạy全 bộ実験? (vd: 6h, overnight, vài ngày?)
- **C.** ResNet-18 + ViT training: bạn cần train từ scratch hay fine-tune pretrained ImageNet? (gợi ý: pretrained cho nhanh, đủ VRAM 4GB với batch 32 + AMP).
- **D.** ViT nhẹ bạn muốn dùng checkpoint nào? Gợi ý: `google/vit-base-patch16-224` (giống paper TripoSR không dùng ViT cho reconstruct, chỉ cho label), hoặc `timm/vit_tiny_patch16_224` (5–7 MB, chạy dễ trên 4GB). Bạn chọn.

### Câu hỏi 5 — Phạm vi báo cáo LaTeX

- **A.** `main.tex` của niên luận nằm ở đâu? (tôi chưa thấy `.tex` trong repo — có thể ngoài 3DGame). Tôi sẽ sinh fragment vào `experiments/outputs/tables/*.tex` rồi bạn `\input{}`, không sửa `.tex` gốc.
- **B.** Số chữ số thập phân thống nhất? Gợi ý: Accuracy/F1 4 số, CD 6 số, F-score 2 số, thời gian 3 số. Bạn xác nhận.
- **C.** Ngôn ngữ bảng: tiếng Việt hay tiếng Anh? Gợi ý: nhãn tiếng Việt (theo prompt) nhưng giữ thuật ngữ kỹ thuật Anh trong ngoặc.

---

> Sau khi bạn trả lời 5 câu hỏi, tôi sẽ sang Giai đoạn 1 (tạo `experiments/` scaffolding + YAML configs + README), không sửa code cũ. Tôi sẽ dừng và báo cáo sau Giai đoạn 1 trước khi tiếp Giai đoạn 2.
