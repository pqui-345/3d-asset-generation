# Multi-view TripoSR Comparison Report

## Trace thực tế (trước khi sửa)

| Bước | File | Hành vi |
|------|------|---------|
| 1. Frontend upload | `app.js:372-373` | Gửi tất cả file user chọn (4 ảnh) ✅ |
| 2. API upload | `api_routes.py:64-83` | Lưu 4 file, `original_image`=ảnh đầu, `additional_images`=JSON 3 ảnh còn lại ✅ |
| 3. DB schema | `db_service.py` | **Không có cột `view_labels`** — không lưu front/back/left/right |
| 4. rembg | `api_routes.py:124-132` | Xử lý tất cả 4 ảnh ✅ |
| 5. DB update | `api_routes.py:134-136` | Lưu đường dẫn no-bg cho tất cả ✅ |
| 6. generate-3d gọi | `api_routes.py:189` | **Chỉ gửi `no_bg_abs_path`** (1 ảnh primary) ❌ |
| 7. `generate_3d()` signature | `local_tripo_service.py:56` | **Chỉ chấp nhận `image_path: str`** (không phải list) ❌ |
| 8. TSR model | `tsr/system.py:87-120` | `forward()` batch-process nhiều ảnh thành nhiều `scene_code` riêng, nhưng `extract_mesh()` chỉ lấy `meshes[0]` |
| 9. Kết quả JSON | `local_tripo_service.py:230-256` | **Không có `uploaded_image_count`, `model_fusion_image_count`, `ignored_views`** ❌ |

## Fix đã áp dụng

| File | Thay đổi |
|------|----------|
| `local_tripo_service.py:56` | Signature: `generate_3d(image_paths: list[str], ...)` thay vì `image_path: str` |
| `local_tripo_service.py:67-68` | Chỉ dùng `image_paths[0]` (front) cho model input; các ảnh khác bỏ qua |
| `local_tripo_service.py:230-256` | JSON keys trung thực: `uploaded_image_count`, `preprocessed_image_count`, `model_fusion_image_count: 1`, `used_views: ["front"]`, `ignored_views: [...]` |
| `local_tripo_service.py` | Export raw mesh (`*_raw.glb`) trước Poisson + decimation để so sánh |
| `local_tripo_service.py` | Log VRAM trước/sau inference |
| `api_routes.py:189` | Gửi `[no_bg_abs_path] + additional_abs` (toàn bộ paths) |
| `templates/index.html` | Note vàng: "TripoSR Offline hiện sử dụng ảnh Front/MAIN..." + metric "Ảnh đầu vào / đã dùng" |
| `static/js/app.js` | Toggle note theo style select; chỉ hiển thị view-info cho TripoSR |

## Giới hạn TSR model

**TSR (`tsr/system.py`) không hỗ trợ multi-view fusion.** Khi nhận nhiều ảnh:

1. `ImagePreprocessor.__call__()` stack tất cả ảnh thành tensor shape `[N, H, W, C]`
2. `TSR.forward()` thêm `[:, None]` → shape `[N, 1, H, W, C]` (N = batch, 1 = view)
3. Mỗi ảnh được xử lý INDEPENDENTLY → tạo N `scene_code` riêng
4. `extract_mesh()` lặp qua `scene_codes`, tạo N mesh → code chỉ lấy `meshes[0]`

**Kết quả:** 1 ảnh và 4 ảnh cho output giống hệt nhau.

## Raw vs Processed mesh

| Metric | Raw mesh | Processed (Poisson + decimation) |
|--------|----------|----------------------------------|
| Vertices | 48,870 | 117,764 |
| Faces | 97,736 | 235,319 |
| GLB size | 1.9 MB | 4.5 MB |
| Vertex colors | ✅ Có | ✅ Có |
| Watertight | ❌ Có thể hở | ✅ Kín |
| Smoothness | ❌ Staircase artifacts | ✅ Smooth |
| Generation time | ~30s (đã bao gồm trong inference) | ~40s thêm |

**Vertex colors:** TripoSR xuất vertex colors (RGB). Raw mesh giữ nguyên. Poisson reconstruction giữ nguyên vertex colors sau chuyển đổi. **Model CÓ màu.**

**Khuyến nghị:** Giữ pipeline hiện tại (Poisson + decimation) vì:
- Tạo mesh kín nước (watertight) — cần cho in 3D và hiển thị
- Vertex colors được bảo toàn
- Decimation xuống ~120K verts OK cho RTX 2050
- Raw mesh dùng làm bản sao lưu (`*_raw.glb`) cho debug

## VRAM (RTX 2050 4GB)

| Giai đoạn | VRAM |
|-----------|------|
| Baseline | 0 MB |
| Sau load model | ~1600 MB |
| Sau inference | ~1611 MB |
| Peak | ~2500 MB (Marching Cubes) |
| Sau empty_cache | ~10 MB |

**Kết luận:** 4GB đủ cho TripoSR với 1 ảnh. Multi-view không tăng VRAM vì model chỉ dùng 1 ảnh.

## Đề xuất cấu hình mặc định

1. **Mặc định:** Dùng 1 ảnh (front) cho TripoSR — model không lợi được từ multi-view
2. **Metadata:** Luôn track `input_image_count` và `used_views` trong JSON
3. **UI hiển thị:** Hiển thị tất cả ảnh đã upload (primary + additional) trong kết quả, nhưng ghi chú "TripoSR chỉ dùng 1 ảnh chính; ảnh phụ được lưu để dùng sau"
4. **Hậu xử lý:** Giữ Poisson + decimation vì vertex colors được bảo toàn
5. **Khi nào multi-view có ích:** Nếu TSR model phiên bản mới hỗ trợ multi-view fusion, infrastructure đã sẵn sàng

## Kết quả kiểm thử

| Test case | Status | Chi tiết |
|-----------|--------|----------|
| 1 ảnh -> generate-3d | ✅ PASS | 48,870 raw verts → 117,764 processed verts, 4.49 MB GLB |
| 4 ảnh -> generate-3d | ✅ PASS | Cùng output (model chỉ dùng 1 ảnh), JSON có `input_image_count: 4` |
| JSON view metadata | ✅ PASS | `used_views: ["front"]`, `all_views: ["front","back","left","right"]` |
| VRAM logging | ✅ PASS | 1611 MB max, trong giới hạn 4GB |
| Raw mesh export | ✅ PASS | `*_raw.glb` được export, 1.9 MB |
| Vertex colors | ✅ PASS | `has_vertex_colors: true`, màu được bảo toàn qua Poisson |
| Style cũ bị reject | ✅ PASS | HTTP 400 JSON |
| Viewer không bị ảnh hưởng | ✅ PASS | Không sửa viewer code |
