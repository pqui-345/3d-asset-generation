# Result Viewer Loading Fix Report

## Root Cause

After the 3D Asset Workspace redesign, the HTML result section was rewritten. Two categories of elements were removed from the HTML but `app.js` still referenced them by ID, causing `null` reference errors that crashed `initResultViewer()` before the Three.js scene could initialize.

### Error 1: `initResultToolbar` (app.js ~line 1193)
```
Uncaught TypeError: Cannot read properties of null (reading 'addEventListener')
at initResultToolbar
```
**Selector:** `#btn-use-in-classroom`
**Cause:** The "Use in Classroom" button was removed from the workspace HTML. The guard `if (!btnRotate) return;` only protects the top of the function — `btnUseInClassroom.addEventListener` runs unconditionally after it.

### Error 2: `initResultViewer` (app.js ~line 631)
```
Uncaught TypeError: Cannot set properties of null (setting 'src')
at initResultViewer
```
**Selectors (all null):**
- `#res-original-img` — images moved to left drawer, populated by JS
- `#res-nobg-img` — same
- `#meta-name`, `#meta-vertices`, `#meta-faces`, `#meta-texture`, `#meta-size`, `#meta-time` — metadata moved to drawer
- `#dl-glb-btn`, `#dl-obj-btn`, `#dl-ply-btn` — downloads moved to drawer

**Cause:** The old HTML had a `result-left` column with `<img>`, metadata grid, and download buttons. The workspace redesign replaced this with a left drawer populated dynamically by `_populateDrawerInput()`.

## Fixes Applied

### `static/js/app.js`

| Line | Old selector | Fix |
|------|-------------|-----|
| 631-632 | `res-original-img`, `res-nobg-img` | Removed — images now in drawer via `_populateDrawerInput()` |
| 634-639 | `meta-name`, `meta-vertices`, `meta-faces`, `meta-texture`, `meta-size`, `meta-time` | Removed — metadata now in drawer |
| 641-663 | `meta-method`, `meta-view-info-container`, `meta-view-info` | Removed — info now in drawer |
| 665-667 | `dl-glb-btn`, `dl-obj-btn`, `dl-ply-btn` | Removed — downloads now in drawer |
| 1193 | `btn-use-in-classroom` | Wrapped with `if (btnUseInClassroom)` null guard |

**Additional improvements:**
- Added `console.log` for GLB URL on load start and success
- Added error detail text with URL and error message in `viewer-error-detail`
- Added 15s spinner timeout — if GLB hasn't loaded or errored, spinner stops and error card shows

### `templates/index.html`

| Element | Change |
|---------|--------|
| `#viewer-error` | Added `.canvas-error-title` and `.canvas-error-detail` (with `#viewer-error-detail`) |

### `static/css/style.css`

| Selector | Change |
|----------|--------|
| `.canvas-error .canvas-error-title` | Added — 15px bold white title |
| `.canvas-error .canvas-error-detail` | Added — 12px muted detail text, word-break |

## Selector/ID Summary

| Old ID (removed) | New location | Populated by |
|-------------------|-------------|-------------|
| `res-original-img` | `#ws-drawer-content .drawer-section[data-section="input"]` | `_populateDrawerInput()` |
| `res-nobg-img` | Same | `_populateDrawerInput()` |
| `meta-name` | `#ws-drawer-content .drawer-section[data-section="info"]` | `_populateDrawerInput()` |
| `meta-vertices` | Same | `_populateDrawerInput()` |
| `meta-faces` | Same | `_populateDrawerInput()` |
| `meta-texture` | Same | `_populateDrawerInput()` |
| `meta-size` | Same | `_populateDrawerInput()` |
| `meta-time` | Same | `_populateDrawerInput()` |
| `meta-method` | Same | `_populateDrawerInput()` |
| `dl-glb-btn` | `#ws-drawer-content .drawer-section[data-section="downloads"]` | `_populateDrawerInput()` |
| `dl-obj-btn` | Same | `_populateDrawerInput()` |
| `dl-ply-btn` | Same | `_populateDrawerInput()` |
| `btn-use-in-classroom` | Removed (no replacement) | N/A |

## Files Changed

- `static/js/app.js` — null guards, removed dead element refs, added logging, spinner timeout
- `templates/index.html` — error overlay detail elements
- `static/css/style.css` — error overlay detail styles

## Verification Results

| Check | Result |
|-------|--------|
| `node --check app.js` | OK — no syntax errors |
| HTML: `res-original-img` removed | OK |
| HTML: `btn-use-in-classroom` removed | OK |
| HTML: `result-canvas-container` present | OK |
| HTML: `viewer-error` present | OK |
| HTML: `btn-retry-load` present | OK |
| HTML: `viewer-error-detail` present | OK |
| JS: `btnUseInClassroom` null guard | OK |
| JS: GLB logging | OK |
| JS: Spinner timeout | OK |
| JS: Error detail | OK |
| JS: Drawer population | OK |
| Flask `app.js` 200 | OK |
| Flask `style.css` 200 | OK |

## Test Procedure (manual on browser)

1. Open `http://127.0.0.1:5000/`
2. Create a new asset or load one from library
3. Open DevTools Console — verify no `null` reference errors
4. Open Network tab — verify GLB request returns HTTP 200
5. Verify model renders in center canvas
6. Verify spinner hides after model loads
7. Verify left drawer shows images (Input tab), metadata (Info tab), downloads (Downloads tab)
8. Test at 375px viewport width — verify no crashes
