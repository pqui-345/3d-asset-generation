# Editor UX Optimization Report (v2 - TransformControls Integration)

## Layout trước đây

**Trang kết quả** có 2 cột CSS grid (`1.2fr 2fr`):

```
+------------------+----------------------------+
|  Left Panel      |  Right Panel               |
|  - Ảnh gốc       |  - Three.js Viewer         |
|  - Ảnh tách nền  |  - Toolbar floating        |
|  - Metadata      |  - Orientation bar         |
|  - Downloads     |  - Camera presets          |
+------------------+----------------------------+
|  Mini 3D Asset Editor (dạng form dài phía dưới) |
+--------------------------------------------------+
```

Vấn đề:
- Editor nằm dưới viewer → không vừa chỉnh vừa thấy model
- Tất cả controls hiển thị dọc cùng lúc → khó tìm, rối mắt
- Chữ/nút quá nhỏ (12px), thiếu label và giá trị hiện tại
- Không responsive trên tablet/mobile

## Layout mới (v2 - final)

### Desktop ≥ 1200px: 3-column CSS Grid

```
+----------------------------+-----------------------+-----------+
| Left 280px (2 cột <1200px) | Center 1fr           |Right 320px|
| Ảnh gốc                    | Three.js Viewer      | Editor    |
| Ảnh tách nền               | Gizmo toolbar (top)  | Tabs:     |
| Metadata                   | Floating: toolbar,   | Transform |
| Downloads                  | orient bar, camera   | Vật liệu  |
|                            | presets              | Sticker   |
|                            |                      | Lịch sử   |
+----------------------------+-----------------------+-----------+
```

- Gizmo bar trong viewer (5 nút: Tịnh tiến/Xoay/Scale/Tắt + Đặt đáy + Reset)
- Transform tab: gizmo mode row đồng bộ + quick actions (Đặt đáy/Reset) + collapsible "Tinh chỉnh" (15°/90°, Scale)
- `result-header` compact (flex row, border-bottom) thay cho `text-center mb-5`

### Breakpoints

| Màn hình   | Layout |
|------------|--------|
| ≥ 1200px   | 3 cột grid: `280px 1fr 320px`. Editor cột phải cố định, tab bar luôn visible. |
| 768-1199px | 2 cột: left + center + drawer phải 340px floating (`.editor-drawer-toggle.float`). |
| < 768px    | 1 cột: center full-width + bottom sheet 70vh (`.editor-drawer-toggle.float`). |

### Editor panel

**Header** (dòng 1, border-bottom):
- Tiêu đề: "Tài nguyên 3D" (compact)
- Nút: Undo | Redo | Lưu | Xuất GLB

**Tabs** (4 tab, tab bar luôn visible, Transform mặc định):
1. **Transform** — Gizmo row (3 nút: Tịnh tiến/Xoay/Scale + Tắt gizmo) + quick actions (Đặt đáy/Reset) + collapsible "Tinh chỉnh" (Rotation 15°/90°, Scale slider + preset)
2. **Vật liệu** — Color picker + hex, Metallic/Roughness slider, Áp dụng/Khôi phục
3. **Sticker** — Mode toggle, Màu + Kích thước + Shape, Count, Sticker list, Delete
4. **Lịch sử** — Undo/Redo count + buttons

**Tương tác:**
- Desktop ≥1200px: editor là cột 3, `_toggleEditor()` collapse ẩn/hiện (scaleX 0→1, transition 0.3s)
- Tablet 768-1199: drawer fixed phải 340px, `.open` class
- Mobile <768: bottom sheet 70vh, `.open` class
- `editor-drawer-toggle.float` nút floating trong viewer (góc phải)
- `editor-backdrop` overlay khi drawer/bottom-sheet mở

### Gizmo (TransformControls)

- THREE.TransformControls (r128) từ CDN, khởi tạo sau OrbitControls
- Attach vào `modelRoot` (không phải scene), `transformControls.setSize(0.8)`
- `dragging-changed`: `space bar` toggle không cần disable, set `orbitControls.enabled = !dragging`
- `mouseUp` / `pointerUp`: lưu snapshot (history)
- Gizmo bar viewer + gizmo row editor: đồng bộ active state, cùng set mode `translate|rotate|scale|''`

## File đã sửa

### `static/css/style.css`

**Thay đổi:**
- Breakpoint từ 1500px→1200px, thêm 768-1199px và <768px
- `.result-layout`: grid 3 cột `280px 1fr 320px` (≥1200px)
- `.result-header`: compact flex row, border-bottom (thay `.text-center.mb-5`)
- `.viewer-gizmo-bar`, `.viewer-gizmo-btn`: gizmo toolbar absolute top-left
- `.editor-gizmo-row`, `.editor-gizmo-btn`: editor gizmo mode buttons
- `.editor-collapse-trigger`, `.editor-collapse-content`: collapsible "Tinh chỉnh"
- `.editor-drawer-toggle.float`: floating button; `.editor-backdrop`: overlay
- Responsive override: drawer 340px (768-1199), bottom sheet 70vh (<768)
- `.editor-group`: padding 10px, border-radius 8px; `.editor-btn`: font 14px, min-height 36px

### `templates/index.html`

**Thay đổi:**
- Thêm TransformControls CDN script (`//cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`)
- Thêm `<div class="viewer-gizmo-bar">` với 5 nút gizmo + Đặt đáy/Reset
- Đổi `<div class="text-center mb-5">` thành `<div class="result-header">`
- Đổi drawer toggle từ static bar sang `.editor-drawer-toggle.float` floating trong viewer

### `static/js/asset_editor.js`

**Thay đổi v2:**
- Transform tab: gizmo row (3 btn mode + disable) + quick actions (Đặt đáy/Reset) + collapsible "Tinh chỉnh" chứa rotate 15°/90°, scale slider+preset
- Gizmo đồng bộ active state: `document.querySelectorAll('.gizmo-btn[data-gizmo]')` + `.editor-gizmo-btn[data-gizmo]`
- `_centerModel()` method giữ nhưng không còn button trong Transform tab
- Các tab khác (Vật liệu/Sticker/Lịch sử) giữ nguyên

### `static/js/app.js`

**Thay đổi v2:**
- `initResultViewer()`: thêm `THREE.TransformControls` sau OrbitControls, attach `modelRoot`, `setSize(0.8)`, `dragging-changed` handler, `pointerUp` → snapshot
- `initResultToolbar()`: handlers cho `.gizmo-btn[data-gizmo]`, `#gizmo-btn-floor`, `#gizmo-btn-reset`
- `resizeResultViewer()` + ResizeObserver cho `.result-canvas-container`
- `window.onViewerResize = resizeResultViewer` (gọi từ AssetEditor.openDrawer)

## Kết quả test

| Hạng mục | Trạng thái |
|----------|------------|
| Flask HTML 200 + đủ class mới | OK |
| style.css 200 | OK |
| asset_editor.js 200 | OK |
| app.js 200 | OK |
| JS syntax (Node check) | OK |
| result-header + gizmo-bar + editor-drawer-toggle.float | OK |
| Editor tabs (4 tab) + collapsible Tinh chỉnh | OK |
| TransformControls CDN script include | OK |
| Gizmo bar viewer (5 btn) + gizmo row editor (4 btn) | OK |
| Backdrop element | OK |
| ResizeObserver | OK |

## Kiểm thử tay (cần thực hiện trên browser)

1. **Desktop 1920px**: mở `http://127.0.0.1:5000/`, load model → gizmo bar top-left viewer, editor cột phải 320px
2. **Gizmo**: click "Xoay" → vòng xoay 3 trục xuất hiện quanh model, drag → model xoay, orbit disabled, thả chuột → orbit enabled, snapshot lưu
3. **Gizmo viewer ↔ editor**: click "Scale" ở viewer → editor gizmo row cập nhật active; click "Tắt" ở editor → viewer gizmo tắt
4. **Tablet 1024px**: grid 2 cột, floating button "Chỉnh sửa" trong viewer → click → drawer phải 340px
5. **Mobile 480px**: grid 1 cột, floating button → bottom sheet 70vh
6. **Transform tab**: chevron "Tinh chỉnh" → collapse ẩn/hiện rotate+scale; click 15° → model xoay
7. **Material tab**: color picker → Áp dụng → model đổi màu
8. **Undo/Redo**: xoay model → Undo → model về vị trí cũ
9. **Collapse editor**: `_toggleEditor()` → editor thu gọn (scaleX 0), viewer giãn
10. **Lưu & Xuất GLB**: header buttons hoạt động
