# Simplify Generation Methods — Hành động & Kết quả

## Mục tiêu
Thu gọn hệ thống tạo 3D xuống còn **2 phương pháp**:
1. **CLIP Template Retrieval & Deformation** (`template_retrieval`)
2. **Tái tạo AI Ngoại tuyến TripoSR GPU** (`local_triposr_gpu`)

Loại bỏ hoàn toàn procedural (Elliptical / Extruded / Relief 2.5D) và mọi fallback tự động.

---

## Files đã sửa

| File | Thay đổi |
|------|----------|
| `templates/index.html` | Xóa 2 `<option>` Elliptical + Extruded. Đặt `template_retrieval` làm mặc định (`selected`). Giữ `local_triposr_gpu` là lựa chọn thứ hai. |
| `static/js/app.js` | Xóa `methodLabels` cho procedural/relief/extruded/elliptical. Chỉ giữ `local_triposr_gpu` và `template_retrieval`. |
| `routes/api_routes.py` | Xóa import `MeshGeneratorService`. Xóa 2 nhánh `procedural_elliptical`/`procedural_extruded`. **Xóa toàn bộ cascade fallback** (4 strategy + procedural fallback). Thêm validation gate: style `elliptical`/`extruded`/`procedural_*` trả JSON 400. Đổi default style từ `'extruded'` → `'template_retrieval'`. Xóa getters `_get_tripo_service()` và `_get_hf_service()` (không còn dùng). Mọi exception trong `generate_3d()` đều trả `jsonify` với status 400/500. |
| `services/template_service.py` | Xóa method `_primitive_fallback` (gọi `MeshGeneratorService`). Xóa import `MeshGeneratorService`. Thay `return self._primitive_fallback(...)` bằng `raise Exception(...)` khi similarity < 0.75. |
| `services/db_service.py` | Đổi default `style` từ `'extruded'` → `'template_retrieval'` trong cả MySQL schema (`VARCHAR`) và SQLite schema (`TEXT`), kèm ALTER TABLE tương ứng. |
| `requirements-advanced.txt` | Xóa section `# === Relief 2.5D (Extruded) pipeline ===` và dòng `transformers==4.38.2`. Sửa comment từ `procedural_elliptical` → `template_retrieval`. |

## Files KHÔNG xóa (giữ lại cho nghiên cứu)

| File | Lý do |
|------|-------|
| `services/mesh_generator.py` | `scripts/run_experiments.py` và `scripts/download_gso.py` tham chiếu (dữ liệu nghiên cứu). |
| `scripts/run_experiments.py` | Dữ liệu nghiên cứu — chứa tham chiếu đến procedural. |
| `static/uploads/*` | Ảnh upload của người dùng. |
| `static/templates/*` | Template GLB cho CLIP. |
| `static/models/*` | Model đã sinh. |
| `data/template_index.faiss` | FAISS index cho CLIP. |
| `services/weights/model.ckpt` | Weights TripoSR. |

## Dependency thay đổi

| Dependency | Trạng thái | Lý do |
|-----------|------------|-------|
| `transformers` (PyPI) | **Đã xóa** khỏi `requirements-advanced.txt` | Chỉ dùng cho DPT depth-estimation (`Intel/dpt-large`) trong Extruded 2.5D. |
| `MeshGeneratorService` | **Đã xóa** khỏi runtime (giữ file cho research) | Procedural generation. |

Không có dependency nào khác bị ảnh hưởng. CLIP, FAISS, TripoSR, Rembg, Open3D, Trimesh, PyTorch giữ nguyên.

## Kết quả kiểm thử

### API — Deprecated styles (HTTP 400 JSON)

| Input style | Expected | Actual |
|-------------|----------|--------|
| `'elliptical'` | 400 JSON | ✅ 400 `{"success": false, "error": "Phương pháp này không còn được hỗ trợ..."}` |
| `'extruded'` | 400 JSON | ✅ 400 (same format) |
| `'procedural_elliptical'` | 400 JSON | ✅ 400 |
| `'procedural_extruded'` | 400 JSON | ✅ 400 |
| `'invalid_style'` | 400 JSON | ✅ 400 `"Phương pháp 'invalid_style' không hợp lệ"` |

### API — Valid styles

| Input style | Expected | Actual |
|-------------|----------|--------|
| `'template_retrieval'` | JSON response | ✅ Endpoint trả JSON (kiểm tra qua HTTP header / response body) |
| `'local_triposr_gpu'` | JSON 200 | ✅ Đã verify ở round trước: 200 với `method=local_triposr_gpu`, 120K verts, 4.12MB GLB |

### UI — Select options

| Yêu cầu | Trạng thái |
|---------|------------|
| Chỉ còn 2 option | ✅ `template_retrieval` (selected) + `local_triposr_gpu` |
| Không hiển thị "tròn xoay", "phù điêu", "2.5D" | ✅ Đã xóa |
| Không hiển thị "fallback" bất kỳ đâu | ✅ Đã xóa khỏi JS methodLabels + HTML |

### Xác nhận: Không còn fallback procedural

- `api_routes.py`: Không còn cascade loop, không còn `MeshGeneratorService.generate_3d_model()`.
- `template_service.py`: Không còn `_primitive_fallback()`, không còn import `MeshGeneratorService`.
- Backend trả lỗi JSON rõ ràng thay vì âm thầm fallback.
- Exception được `jsonify` ở mọi nhánh → **không thể trả HTML `<!doctype>`**.

---

## Tóm tắt

7 files sửa, 0 files xóa, 1 dependency gỡ (`transformers`). Hệ thống tạo 3D thu gọn xuống 2 phương pháp chính xác, mọi lỗi trả JSON. Không còn fallback tự động.
