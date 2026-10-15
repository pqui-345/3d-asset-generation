# Viewer Orientation — Cải thiện Three.js Viewer cho Model TripoSR

## Nguyên nhân model nằm ngang

TripoSR xuất mesh theo hệ trục **Z-up** (chuẩn của 3D reconstruction). GLTF/Three.js dùng **Y-up**. Pipeline export (`local_tripo_service.py:98-99`) đã áp dụng `rotation_matrix(-np.pi/2, [1,0,0])` để chuyển đổi. Tuy nhiên:

1. Three.js `GLTFLoader` có thể áp dụng thêm coordinate transform nếu metadata GLB không nhất quán.
2. Viewer cũ (`app.js` cũ) thêm `gltf.scene` trực tiếp vào `scene` mà **không**:
   - Dùng `modelRoot` group để kiểm soát rotation riêng
   - Tính bounding box để căn giữa + đặt đáy chạm sàn
   - Fit camera theo bounding sphere
3. Auto-rotate quay liên tục quanh Y, không cho người dùng chỉnh hướng.

## Transform đã dùng

### METHOD_ORIENT — Config per method

```javascript
const METHOD_ORIENT = {
    'local_triposr_gpu': {
        rotateX: 0,   // export đã xoay -90° X; viewer mặc định không xoay thêm
        rotateY: 0,
        rotateZ: 0,
        description: 'Mặc định Z-up → Y-up (có thể cần xoay tay)'
    },
    'template_retrieval': {
        rotateX: 0,
        rotateY: 0,
        rotateZ: 0,
        description: 'Template đã đúng trục Y-up'
    }
};
```

Nếu TripoSR model vẫn nằm ngang, người dùng bấm **X+90°** hoặc **X-90°** trên thanh orient để sửa.

### Viewer pipeline sau load

1. `gltf.scene` → thêm vào `THREE.Group()` (`modelRoot`)
2. `Box3.setFromObject(modelRoot)` → tính center → dịch về `(0,0,0)`
3. Scale đồng nhất để max dimension = 1.8
4. Áp dụng `METHOD_ORIENT[method].rotate*` lên `modelRoot.rotation`
5. `Box3` lại → tính `minY` → dịch Y để đáy chạm `y=0`
6. `BoundingSphere` → camera fit: `camera.position = sphere.radius * 2.8`
7. Khôi phục orientation đã lưu (localStorage) nếu có

## File sửa

| File | Thay đổi |
|------|----------|
| `templates/index.html` | Thêm **orientation toolbar** (6 nút xoay + Đặt đứng + Lưu) + **camera presets** (Trái/Phải/Trên/Trước/Góc) + nút **Grid toggle** |
| `static/css/style.css` | Thêm `.viewer-orient-bar`, `.orient-btn`, `.viewer-cam-presets`, `.cam-btn` styles |
| `static/js/app.js` | **Viết lại** `initResultViewer()`: modelRoot group, Box3 center + floor, per-method orientation, camera auto-fit, studio lighting. **Viết lại** `initResultToolbar()`: xử lý orient buttons, camera presets, grid toggle, auto-rotate chỉ khi user click, save/load orientation. Thêm `METHOD_ORIENT` config, `_saveOrientation()`, `_restoreOrientation()`, `_setCameraPreset()`. |

## Các chức năng mới

| Chức năng | Mô tả |
|-----------|-------|
| **Xoay X/Y/Z ±90°** | 6 nút xoay modelRoot theo góc 90° quanh từng trục |
| **Đặt đứng mặc định** | Reset rotation về default của method |
| **Lưu hướng hiển thị** | Lưu `{rotation, position, scale}` vào `localStorage['viewer_orient_<assetId>']`. Ghi rõ "chỉ viewer, không ảnh hưởng file download" |
| **Khôi phục hướng** | Khi mở lại asset, kiểm tra localStorage → áp dụng. Hiển thị hint "Đã khôi phục hướng đã lưu" |
| **Camera presets** | Trước/Trái/Phải/Trên/Góc phối cảnh — fit bounding sphere |
| **Grid toggle** | Ẩn/hiện grid, active mặc định |
| **Auto-rotate** | Chỉ quay khi user bấm nút (không tự động) |
| **Studio lighting** | Ambient 0.35 + Hemisphere 0.5 + Key 2.0 + Fill 0.7 + Rim 0.9 |
| **Shadow mapping** | PCFSoft 2048px, ground plane receive shadow |

## Cách kiểm thử

1. **Khởi động Flask** — `python app.py`
2. **Upload ảnh** → chọn **TripoSR GPU** → generate model
3. **Xem kết quả**: model không còn nằm ngang, căn giữa, chạm sàn
4. **Xoay thử**: bấm X+90°, X-90°, Y+90°,... — model xoay tức thì, tự căn lại sàn
5. **Camera presets**: bấm Trái, Phải, Trên, Trước — camera chuyển view
6. **Lưu hướng**: bấm "Lưu" → refresh trang → mở lại asset → hướng được khôi phục
7. **Grid**: bấm nút grid → ẩn/hiện
8. **Auto-rotate**: bấm nút auto-rotate → model quay chậm; bấm lại → dừng

## Giới hạn

- **Hướng lưu chỉ áp dụng cho viewer** (localStorage), không ghi vào GLB file download.
- Orient save dùng `localStorage` theo `asset_id`, không đồng bộ giữa các máy.
- OBJ fallback (`loadOBJFallback`) không có orientation toolbar — chỉ load đơn giản.
- Nếu model bị lỗi orientation nặng, cần sửa `rotateX` trong `METHOD_ORIENT['local_triposr_gpu']` hoặc dùng UI.
