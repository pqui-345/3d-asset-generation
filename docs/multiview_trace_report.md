# Multi-view Trace Report — Local TripoSR

## Bảng trace

| Bước | Số ảnh nhận được | File/Function | Bằng chứng |
|------|------------------|---------------|------------|
| 1. Frontend upload | 4 ảnh (tất cả file user chọn) | `static/js/app.js:372-373` | `formData.append('files', f)` cho mỗi file trong `selectedFiles` |
| 2. API upload receive | 4 ảnh | `routes/api_routes.py:64-71` | Vòng lặp `for f in files` lưu từng file vào `static/uploads/` |
| 3. DB lưu | `saved_originals[0]` → `original_image`, `saved_originals[1:]` → `additional_images` | `routes/api_routes.py:76-83` | `original_image` lưu 1 ảnh, `additional_images` lưu JSON array (3 ảnh còn lại) |
| 4. DB lưu nhãn góc | **Không** | — | Không có cột `view_labels`, không mapping "front/back/left/right" |
| 5. rembg primary | 1 ảnh | `routes/api_routes.py:124` | `primary_nobg = do_remove(original_rel_path)` |
| 6. rembg additional | 3 ảnh (nếu có) | `routes/api_routes.py:128-132` | Vòng lặp `for img_rel in additional_images` |
| 7. DB update nobg | `no_bg_image` = primary nobg, `additional_images` = nobg paths | `routes/api_routes.py:134-137` | Cả primary + additional được update |
| 8. generate-3d gọi | **CHỈ 1 ảnh** (`no_bg_abs_path` — primary) | `routes/api_routes.py:189` | `lts.generate_3d(no_bg_abs_path, models_dir, asset_slug)` — `additional_abs` có 3 path nhưng không truyền |
| 9. `LocalTripoService.generate_3d()` nhận | **CHỈ 1 ảnh** (`image_path: str`) | `services/local_tripo_service.py:56` | Signature: `def generate_3d(self, image_path, output_dir, asset_name):` |
| 10. `Image.open(image_path)` | 1 ảnh | `services/local_tripo_service.py:67` | `Image.open(image_path)` — chỉ 1 file |
| 11. `self.model(img_rgb, device="cuda")` | 1 ảnh | `services/local_tripo_service.py:84` | Single PIL.Image → TSR.forward() |
| 12. TSR model forward | **Tạo 1 scene_code** duy nhất | `tsr/system.py:87-120` | `rgb_cond[:, None]` shape `[1, 1, H, W, C]`, Nv=1 hardcoded. **Model không hỗ trợ multi-view fusion** |
| 13. extract_mesh | 1 mesh từ `scene_codes[0]` | `services/local_tripo_service.py:92` | `mesh = meshes[0]` |
| 14. JSON result | Không có `input_image_count`, `used_views` | `services/local_tripo_service.py:194-207` | Return dict chỉ có method/vertices/faces |

## Kết luận

**Hệ thống hiện tại CHỈ dùng 1 ảnh (front/main) cho TripoSR.** 3 ảnh additional được upload, lưu DB, tách nền nhưng KHÔNG BAO GIỜ được truyền vào `local_tripo_service.generate_3d()`:

- `api_routes.py:189`: chỉ gửi `no_bg_abs_path` (1 primary)
- `local_tripo_service.py:56`: signature chỉ nhận `image_path` (str, không phải list)
- `local_tripo_service.py:67`: `Image.open(image_path)` — mở đúng 1 file

**TSR model (`tsr/system.py`)** có khả năng batch-process nhiều ảnh (mỗi ảnh cho 1 scene_code riêng), nhưng không có cơ chế fusion multi-view. `extract_mesh()` lấy `meshes[0]` — chỉ dùng mesh từ ảnh đầu tiên.

## Fix đã áp dụng

| File | Thay đổi |
|------|----------|
| `local_tripo_service.py` | JSON keys trung thực: `uploaded_image_count`, `preprocessed_image_count`, `model_fusion_image_count: 1`, `used_views: ["front"]`, `ignored_views: [...]` |
| `api_routes.py` | Gửi `[no_bg_abs_path] + additional_abs` (toàn bộ paths) |
| `templates/index.html` | Thêm note vàng dưới select: "TripoSR Offline hiện sử dụng ảnh Front/MAIN..." + metric "Ảnh đầu vào / đã dùng" |
| `static/js/app.js` | Toggle note theo style select; populate view-info chỉ cho TripoSR |
