# 3D Asset Workspace Redesign Report

## Nguyen nhan viewer trong (Priority 0)

### Van de
Trong giao dien cu, Three.js viewer hien trong/khong thay model. Canvas den, khong co loi hien thi.

### Nguyen nhan goc
1. **CSS height chain bi break**: `.viewer-viewport-box` dung `flex-grow: 1` nhung parent `.viewer-3d-card` co `height: 100%` ma khong co chieu cao ro rang tu parent. `#result-canvas-container` co `height: 100%` nhung parent khong co fixed height -> chieu cao tinh la 0.
2. **Layout cu**: `.result-layout` dung CSS grid `280px 1fr 320px` nhung `.result-center` khong co `min-height` on mobile, gay container nho.
3. **Khong co error handling**: Neu GLB load that bai, canvas den ma khong co message loi hay nut thu lai.

### Cach sua
1. **CSS fix**: Dung `position: absolute; inset: 0` cho `#result-canvas-container` thay vi `height: 100%`. Dieu nay dam bao container luon co kich thuoc bang parent, bat ke parent co fixed height hay khong.
2. **Error overlay**: Them `#viewer-error` overlay hien thi khi GLB load that bai, voi nut "Thu lai" goi lai `initResultViewer()`.
3. **Loading overlay**: Giu `#viewer-loader` overlay hien thi trong qua trinh tai model.
4. **ResizeObserver**: Cap nhat de observe ca `#result-canvas-container` va parent, dam bao resize dung khi panel mo/dong.

## Layout moi: 3D Asset Workspace

### Cau truc HTML

```
<section id="view-result">
  <div class="workspace">
    <div class="ws-topbar">         // Top bar 52px
      <ws-topbar-left>              // Brand + asset name + status
      <ws-topbar-right>             // Save + Export GLB
    </div>
    <div class="ws-body">           // Flex row, flex: 1
      <ws-rail-left>                // Icon rail 52px
      <ws-drawer-left>              // Drawer 280px (slide out)
      <ws-canvas-wrap>              // Flex: 1
        <ws-canvas>                 // position: relative, black bg
          <result-canvas-container> // position: absolute, inset: 0
          <viewer-loader>           // Loading overlay
          <viewer-error>            // Error overlay + retry
        </ws-canvas>
        <ws-bottom-toolbar>         // Floating bottom toolbar
      </ws-canvas-wrap>
      <ws-panel-right>              // Editor panel 320px
        <asset-editor-panel>        // AssetEditor renders here
      </ws-panel-right>
      <ws-panel-toggle>             // Collapse toggle button
    </div>
  </div>
</section>
```

### Top Bar (52px)
- Brand logo "3D" (30x30px)
- Asset name (ellipsis neu dai)
- Status badge "Da tao" (green)
- Save button (icon + text)
- Export GLB button (primary gradient)

### Left Rail (52px)
3 icon buttons:
- **Input** (image icon): Hien thi anh goc + anh da cat nen
- **Info** (info icon): Hien thi metadata (ten, phuong phap, thoi gian, dinh, mat, texture, kich thuoc)
- **Downloads** (download icon): 3 nut tai GLB/OBJ/PLY

Rail buttons `active` -> open drawer, click lai -> dong drawer.

### Left Drawer (280px)
- Slide out tu trai, width transition 0.25s
- Header voi title + nut dong (X)
- Content: 3 sections, chi hien thi section dang chon
- Images: max-height 140px, border-radius 8px
- Transparent bg: checkerboard pattern 16px
- Metadata: 2-column grid, 6 items
- Downloads: 3-column grid, GLB/OBJ/PLY buttons

### Center Canvas
- `position: relative; background: #000`
- `#result-canvas-container`: `position: absolute; inset: 0; width: 100% !important; height: 100% !important`
- Canvas element: `display: block; width: 100% !important; height: 100% !important`
- Loading overlay: spinner + "Dang tai model 3D..."
- Error overlay: warning icon + message + retry button

### Bottom Toolbar (floating)
Groups separated by `|`:
1. **View tools**: Auto-rotate, Pan, Grid, Reset camera, Fullscreen
2. **Camera presets**: Front, Left, Right, Top, Perspective
3. **Gizmo**: Translate, Rotate, Scale, Disable
4. **Quick actions**: Floor, Reset model

Style: `background: rgba(0,0,0,0.7); backdrop-filter: blur(8px); border-radius: 12px`

### Right Panel (320px)
- Editor panel `#asset-editor-panel` (AssetEditor renders tabs: Transform, Vat lieu, Sticker, Lich su)
- Toggle button `ws-panel-toggle`: chevron left/right
- Desktop: collapse/expand (width 320px -> 0)
- Tablet: fixed drawer right
- Mobile: bottom sheet 70vh

## Responsive Breakpoints

| Man hinh | Layout |
|----------|--------|
| >= 1200px | Rail 52px + Drawer 280px (toggle) + Canvas (flex:1) + Panel 320px (toggle) |
| 768-1199px | Canvas full-width. Rail hidden. Drawer fixed left 300px. Panel fixed right 320px. |
| < 768px | Canvas full-width. Rail hidden. Drawer full-width. Panel bottom sheet 70vh. |

### Mobile specifics
- Top bar: 44px height, button text hidden (icon only)
- Drawer: full-width, full-height minus topbar
- Panel: bottom sheet with border-radius 16px top
- Bottom toolbar: smaller buttons (28x28px)

## File da sua

### `templates/index.html`
- Replace entire SECTION 4 (RESULT VIEW) with new workspace layout
- Added: `.workspace`, `.ws-topbar`, `.ws-body`, `.ws-rail-left`, `.ws-drawer-left`, `.ws-canvas-wrap`, `.ws-canvas`, `.ws-bottom-toolbar`, `.ws-panel-right`, `.ws-panel-toggle`
- Added: `.canvas-error` overlay with retry button
- Removed: `.result-header`, `.result-layout`, `.result-left`, `.result-center`, `.result-right`, old floating toolbars

### `static/css/style.css`
- **Added**: Full workspace layout CSS (~300 lines): `.workspace`, `.ws-topbar`, `.ws-rail-left`, `.ws-drawer-left`, `.ws-canvas-wrap`, `.ws-canvas`, `.ws-bottom-toolbar`, `.ws-panel-right`, `.ws-panel-toggle`
- **Added**: Drawer content styles: `.drawer-img-box`, `.drawer-meta-grid`, `.drawer-meta-item`, `.drawer-downloads`, `.drawer-download-btns`
- **Added**: Responsive breakpoints for tablet (768-1199px) and mobile (<768px)
- **Fixed**: `#result-canvas-container` uses `position: absolute; inset: 0` instead of `height: 100%`
- **Hidden**: Old floating toolbars (`.viewer-toolbar`, `.viewer-orient-bar`, `.viewer-cam-presets`, `.viewer-gizmo-bar`, `.editor-drawer-toggle.float`)
- **Hidden**: Legacy layout classes (`.dual-image-card`, `.result-img-box`, `.result-left`, `.result-center`, `.result-right`)
- **Updated**: `#asset-editor-panel` now has `background: transparent; border: none` (inside ws-panel-right)

### `static/js/app.js`
- **Fixed**: `initResultViewer()` - added error overlay handling, workspace init call
- **Fixed**: GLB load error handler shows error overlay instead of OBJ fallback
- **Fixed**: `resizeResultViewer()` - added `clientWidth > 0 && clientHeight > 0` check
- **Fixed**: Fullscreen button references `.ws-canvas` instead of `.viewer-viewport-box`
- **Fixed**: ResizeObserver observes both container and parent
- **Added**: `initWorkspace()` - initializes rail buttons, drawer, panel toggle, top bar buttons
- **Added**: `openLeftDrawer(panel)` / `closeLeftDrawer()` - drawer open/close with content switch
- **Added**: `toggleRightPanel()` - desktop collapse, tablet/mobile toggle
- **Added**: `_populateDrawerInput()` - injects images, metadata, downloads into drawer

### `static/js/asset_editor.js`
- No changes needed (AssetEditor renders into `#asset-editor-panel` which is now inside `.ws-panel-right`)

## Ket qua test

| Hang muc | Trang thai |
|----------|------------|
| Flask HTML 200 | OK |
| Workspace topbar HTML | OK |
| Workspace canvas HTML | OK |
| Left rail HTML | OK |
| Right panel HTML | OK |
| Bottom toolbar HTML | OK |
| Canvas container HTML | OK |
| TransformControls CDN | OK |
| Error overlay HTML | OK |
| style.css 200 | OK |
| app.js 200 | OK |
| asset_editor.js 200 | OK |
| JS syntax (node --check) | OK |
| 33 workspace CSS rules | OK |

## Kiem thu tay (can thuc hien tren browser)

1. **Viewer hien model**: Mo `http://127.0.0.1:5000/`, tao asset moi, kiem tra model 3D hien trong center canvas
2. **Loading overlay**: Khi tai model, overlay "Dang tai model 3D..." hien thi
3. **Error handling**: Neu GLB load loi, overlay loi hien thi voi nut "Thu lai"
4. **Left rail**: Click icon "Anh dau vao" -> drawer truot ra trai, hien thi 2 anh
5. **Left rail**: Click icon "Thong tin" -> drawer chuyen sang metadata
6. **Left rail**: Click icon "Tai xuong" -> drawer hien 3 nut tai GLB/OBJ/PLY
7. **Left rail**: Click lai icon dang active -> drawer dong
8. **Bottom toolbar**: Click cac nut view (auto-rotate, pan, grid, reset, fullscreen)
9. **Bottom toolbar**: Click camera presets (front, left, right, top, perspective)
10. **Bottom toolbar**: Click gizmo (translate, rotate, scale, disable)
11. **Right panel**: Editor tabs hoat dong (Transform, Vat lieu, Sticker, Lich su)
12. **Panel toggle**: Click chevron -> panel thu gon, viewer giai rong
13. **Responsive 1366px**: Grid 2 column, rail hidden, drawer/panel la overlay
14. **Responsive 980px**: Grid 1 column, drawer full-width, panel bottom sheet
15. **Responsive 480px**: Top bar nhat, drawer full-screen, panel bottom sheet
16. **Fullscreen**: Click fullscreen button -> canvas toan man hinh
17. **Gizmo**: Click Translate -> gizmo hien tren model, drag -> model di chuyen
18. **Gizmo**: Click Rotate -> vong xoay 3 truc hien, drag -> model xoay
19. **Material**: Click tab Vat lieu -> chon mau, adjust metallic/roughness, Ap dung
20. **Sticker**: Click tab Sticker -> bat che do, click model de dat sticker
21. **Undo/Redo**: Thao tac xong, click Undo -> model ve trang thai truoc
22. **Save**: Click Save -> editor state duoc luu
23. **Export GLB**: Click Xuat GLB -> file GLB duoc xuat
24. **Library**: Tu home, click "Xem Thu Vien", chon asset -> result view hien dung asset
