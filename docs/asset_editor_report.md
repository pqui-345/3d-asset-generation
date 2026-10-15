# Asset Editor Report — Mini 3D Asset Editor

## Tổng quan

Mini 3D Asset Editor được tích hợp vào result viewer của TripoSR. Sau khi model được sinh, editor panel xuất hiện bên dưới viewport, cho phép hiệu chỉnh cơ bản và xuất tài nguyên đã chỉnh sửa.

## Chức năng đã làm

### 1. Transform Model
| Chức năng | File | Trạng thái |
|-----------|------|------------|
| Xoay X/Y/Z +15°, -15° | `static/js/asset_editor.js` | ✅ |
| Xoay X/Y/Z +90°, -90° | `static/js/asset_editor.js` | ✅ |
| Scale slider 0.1–3.0 | `static/js/asset_editor.js` | ✅ |
| Scale preset 0.5x, 1x, 2x | `static/js/asset_editor.js` | ✅ |
| Đặt đáy chạm mặt sàn (y= -0.5) | `static/js/asset_editor.js` | ✅ |
| Về gốc tọa độ (0,0,0) | `static/js/asset_editor.js` | ✅ |
| Reset toàn bộ transform | `static/js/asset_editor.js` | ✅ |

### 2. Material & Màu
| Chức năng | File | Trạng thái |
|-----------|------|------------|
| Color picker (đổi màu toàn bộ model) | `static/js/asset_editor.js` | ✅ |
| Metallic slider (0–1) | `static/js/asset_editor.js` | ✅ |
| Roughness slider (0–1) | `static/js/asset_editor.js` | ✅ |
| Nút "Áp dụng màu mới" (clone material gốc trước khi ghi đè) | `static/js/asset_editor.js` | ✅ |
| Nút "Khôi phục vật liệu gốc" | `static/js/asset_editor.js` | ✅ |

### 3. Sticker giáo dục
| Chức năng | File | Trạng thái |
|-----------|------|------------|
| Raycasting click để đặt sticker lên bề mặt | `static/js/asset_editor.js` | ✅ |
| Sprite-based decal (circle/square texture) | `static/js/asset_editor.js` | ✅ |
| Chọn sticker bằng click | `static/js/asset_editor.js` | ✅ |
| Xóa sticker | `static/js/asset_editor.js` | ✅ |
| Đổi màu sticker | `static/js/asset_editor.js` | ✅ |
| Đổi kích thước sticker | `static/js/asset_editor.js` | ✅ |
| Đổi hình (circle/square) | `static/js/asset_editor.js` | ✅ |
| Giới hạn 20 sticker | `static/js/asset_editor.js` | ✅ |
| Danh sách sticker hiển thị trong panel | `static/js/asset_editor.js` | ✅ |

### 4. Viewer
| Chức năng | File | Trạng thái |
|-----------|------|------------|
| Camera presets: Front/Back/Left/Right/Top/Perspective | Vốn có trong `app.js` | ✅ |
| Ẩn/hiện grid | Vốn có trong `app.js` | ✅ |
| Bật/tắt auto rotate | Vốn có trong `app.js` | ✅ |
| Undo/Redo (Ctrl+Z / Ctrl+Shift+Z) | `static/js/asset_editor.js` | ✅ |
| Undo/Redo buttons trong panel | `static/js/asset_editor.js` | ✅ |

### 5. Lưu & Export
| Chức năng | File | Trạng thái |
|-----------|------|------------|
| Lưu editor state (transform + material + sticker) theo asset_id | `static/js/asset_editor.js` + `routes/api_routes.py:366` | ✅ |
| Mở lại asset khôi phục trạng thái | `static/js/asset_editor.js` + `routes/api_routes.py:383` | ✅ |
| Nút "Xuất GLB đã chỉnh sửa" | `static/js/asset_editor.js` | ✅ |
| Dùng GLTFExporter để export scene | `static/js/asset_editor.js` | ✅ |
| Decode base64, lưu file, update DB | `routes/api_routes.py:420` | ✅ |

### 6. Backend
| Chức năng | File | Trạng thái |
|-----------|------|------------|
| Cột `editor_state TEXT` trong DB | `services/db_service.py:81,120` | ✅ |
| POST `/api/assets/<id>/editor-save` | `routes/api_routes.py:358` | ✅ |
| GET `/api/assets/<id>/editor-load` | `routes/api_routes.py:369` | ✅ |
| POST `/api/assets/<id>/export-edited` | `routes/api_routes.py:386` | ✅ |

## Dữ liệu được lưu

Editor state JSON được lưu vào cột `editor_state` trong bảng `assets`:

```json
{
  "transform": {
    "position": [x, y, z],
    "rotation": [x, y, z], 
    "scale": [x, y, z]
  },
  "material": {
    "color": "#rrggbb",
    "metallic": 0.0,
    "roughness": 0.5,
    "applied": false
  },
  "stickers": [
    {
      "id": "sticker_1",
      "position": [x, y, z],
      "normal": [nx, ny, nz],
      "color": "#ff0000",
      "size": 0.08,
      "shape": "circle"
    }
  ]
}
```

## Export GLB

- Dùng `THREE.GLTFExporter` (r128) parse scene → GLB binary → base64 → POST → server decode → lưu file `.glb`.
- Transform và material override được export vào GLB.
- **Sticker KHÔNG được export vào GLB.** Sticker là Sprite (billboard) trong Three.js, không được GLTF format hỗ trợ. Khi export, sticker chỉ tồn tại trong viewer và editor state. Người dùng được thông báo: "Sticker chỉ lưu trong viewer".

## Giới hạn còn lại

### Sticker
- Dùng Sprite thay vì DecalGeometry (DecalGeometry yêu cầu thêm dependencies và có vấn đề với import style cũ).
- Sticker là billboard (luôn quay về camera), không dán chặt vào bề mặt như decal thật.
- Sticker **không export được vào GLB** — chỉ hiển thị trong viewer.

### Material
- Color picker đổi màu toàn bộ model (tất cả mesh), không hỗ trợ chọn từng mesh riêng.
- Không hỗ trợ texture mapping hay multi-material.
- Không có gradient/shader editor.

### Transform
- Không có gizmo kéo thả (Translate/Rotate/Scale gizmo).
- Xoay theo bước 15°, không có xoay tự do.

### Undo/Redo
- Stack tối đa 50 snapshot.
- Không có history panel để xem danh sách.

### Export
- Sticker không thể export.
- Export dùng base64 + POST → server → file — không phải download trực tiếp.
- GLTFExporter có thể không tương thích 100% với toàn bộ scene (materials, textures).

### Backend
- `editor_state` được lưu nhưng chưa có cơ chế cleanup (các state cũ không tự động xóa).
- Export overwrite file GLB mới nhất, không versioning.

## Files đã thay đổi

| File | Thay đổi |
|------|----------|
| `static/js/asset_editor.js` | **Mới** — toàn bộ editor (955 dòng) |
| `static/css/style.css` | Thêm editor CSS (~200 dòng) |
| `routes/api_routes.py` | Thêm 3 API endpoints (editor-save, editor-load, export-edited) + import base64 |
| `services/db_service.py` | Thêm cột `editor_state` TEXT (migration MySQL + SQLite) |
| `templates/index.html` | Thêm div editor panel + 2 script includes (GLTFExporter, asset_editor.js) |
| `static/js/app.js` | Thêm khởi tạo AssetEditor sau khi model load |
