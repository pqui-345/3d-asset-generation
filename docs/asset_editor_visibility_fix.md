# Asset Editor Visibility Fix Report

## Vấn đề

Sau khi tích hợp Mini 3D Asset Editor, panel editor **không hiển thị** trên giao diện người dùng. Model TripoSR load thành công, viewer hoạt động, nhưng không có panel "Chỉnh sửa tài nguyên 3D" nào xuất hiện.

## Nguyên nhân gốc

### 1. HTML `display:none` không được gỡ bỏ bởi JS

Trong `templates/index.html`, div chứa editor panel có inline style `display:none`:

```html
<div id="asset-editor-panel" style="display:none; margin-top:24px;"></div>
```

Hàm `AssetEditor.init()` và `renderPanel()` fill nội dung vào div nhưng **không bao giờ set** `panel.style.display = 'block'` để gỡ `display:none`.

Kết quả: panel có đầy đủ HTML (button, slider, label) nhưng bị ẩn hoàn toàn.

### 2. Thiếu error handling khi khởi tạo

Trong `static/js/app.js`, việc gọi `new AssetEditor(...)` không có `try/catch`. Nếu có bất kỳ lỗi JS nào trong constructor/init, editor silently fails mà không có thông báo UI.

## File đã sửa

### `static/js/asset_editor.js` (dòng 59-67)

**Trước:**
```js
init: function () {
    this._saveInitialState();
    this._cacheElements();
    this._bindShortcuts();
    this.renderPanel();
    this._initClickHandlers();
    this.loadEditorState();
},
```

**Sau:**
```js
init: function () {
    if (!this.container) {
        console.error('[AssetEditor] Container not found');
        var fallback = document.getElementById('asset-editor-panel');
        if (!fallback) {
            console.error('[AssetEditor] #asset-editor-panel missing in HTML');
            return;
        }
        this.container = fallback;
    }
    this.container.style.display = 'block';
    this._saveInitialState();
    this._cacheElements();
    this._bindShortcuts();
    this.renderPanel();
    this._initClickHandlers();
    this.loadEditorState();
},
```

**Thay đổi:**
- `this.container.style.display = 'block'` — gỡ inline `display:none`
- Null check + fallback `getElementById` nếu container ban đầu không tìm thấy
- Return sớm nếu container thực sự không tồn tại (tránh lỗi cascade)

### `templates/index.html` (dòng 405)

**Trước:**
```html
<div id="asset-editor-panel" style="display:none; margin-top:24px;"></div>
```

**Sau:**
```html
<div id="asset-editor-panel" style="margin-top:24px;"></div>
```

**Thay đổi:** Xóa `display:none` — JS sẽ quyết định hiển thị khi init.

### `static/js/app.js` (dòng 804-815)

**Trước:**
```js
if (typeof AssetEditor !== 'undefined') {
    AppState.editor = new AssetEditor('asset-editor-panel', scene, camera, controls, modelRoot, assetId);
    AppState.editor.init();
}
```

**Sau:**
```js
if (typeof AssetEditor !== 'undefined') {
    try {
        AppState.editor = new AssetEditor('asset-editor-panel', scene, camera, controls, modelRoot, assetId);
        AppState.editor.init();
    } catch (e) {
        console.error('[AssetEditor] Init failed:', e);
        var ep = document.getElementById('asset-editor-panel');
        if (ep) ep.innerHTML = '<div class="editor-status error" style="display:block; padding:20px;">Editor khởi tạo thất bại: ' + e.message + '</div>';
    }
} else {
    console.warn('[AssetEditor] not loaded — check script include order');
    var ep = document.getElementById('asset-editor-panel');
    if (ep) ep.innerHTML = '<div class="editor-status error" style="display:block; padding:20px;">AssetEditor không được tải — kiểm tra network tab</div>';
}
```

**Thay đổi:**
- `try/catch` bắt lỗi init, hiển thị thông báo UI
- Fallback message nếu `AssetEditor` không tồn tại (script không load)

## Xác minh

1. Mở `http://127.0.0.1:5000/` trong Chrome/Firefox
2. Upload ảnh, chọn TripoSR GPU, Generate
3. Sau khi model 3D hiện trong viewer, panel editor xuất hiện bên dưới với tiêu đề các nhóm:
   - BIẾN ĐỔI (TRANSFORM) — các nút xoay + scale + đặt đáy
   - VẬT LIỆU (MATERIAL) — color picker + slider metallic/roughness
   - STICKER — màu/kích thước/hình + nút chế độ
   - Viewer — Undo/Redo/Lưu/Xuất GLB
4. Click nút "X+90" — model xoay 90°, kiểm tra bằng mắt thường
5. Click nút "Reset" — model về trạng thái ban đầu
6. Hard reload (Ctrl+Shift+R) để clear cache → panel vẫn hiện

## Screenshot

(Không thể chụp tự động — xác nhận bằng tay trên browser)

## Kết luận

Root cause đơn giản: **quên set `display: block`** khi render panel. Fix gồm 3 file, tổng cộng ~15 dòng thay đổi, thêm error handling để dễ debug sau này.
