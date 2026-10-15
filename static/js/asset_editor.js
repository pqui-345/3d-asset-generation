/**
 * AssetEditor — Mini 3D Asset Editor for TripoSR-generated models.
 * Three.js r128, old-style script includes (no ES modules).
 */
function AssetEditor(containerId, scene, camera, controls, model, assetId) {
    this.container = document.getElementById(containerId);
    this.scene = scene;
    this.camera = camera;
    this.controls = controls;
    this.model = model;
    this.assetId = assetId;

    // Transform state
    this._initialTransform = null;

    // Material state
    this._originalMaterials = new Map();
    this._materialApplied = false;
    this._currentColor = '#cccccc';
    this._currentMetallic = 0.0;
    this._currentRoughness = 0.5;

    // Sticker state
    this.stickers = [];
    this._stickerIdCounter = 0;
    this._selectedStickerIdx = -1;
    this._stickerMode = false;
    this._stickerColor = '#ff0000';
    this._stickerSize = 0.08;
    this._stickerShape = 'circle';
    this._maxStickers = 20;

    // Raycaster
    this._raycaster = new THREE.Raycaster();
    this._mouse = new THREE.Vector2();

    // Click-drag guard
    this._pointerDownPos = { x: 0, y: 0 };

    // Undo / Redo
    this._undoStack = [];
    this._redoStack = [];
    this._MAX_UNDO = 50;
    this._snapshotInProgress = false;

    // Status
    this._statusTimer = null;

    AppState.editor = this;
    window.editor = this;
}

AssetEditor.prototype = {

    // ──────────────────────────────────────────────
    //  INIT
    // ──────────────────────────────────────────────

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

    destroy: function () {
        if (this._statusTimer) clearTimeout(this._statusTimer);
        if (this._stickAnimId) {
            cancelAnimationFrame(this._stickAnimId);
            this._stickAnimId = null;
        }
        for (var i = 0; i < this.stickers.length; i++) {
            this.scene.remove(this.stickers[i].mesh);
            this.stickers[i].mesh.material.map.dispose();
            this.stickers[i].mesh.material.dispose();
        }
        this.stickers = [];
        if (this.container) this.container.innerHTML = '';
        if (AppState.editor === this) AppState.editor = null;
        window.editor = null;
    },

    // ──────────────────────────────────────────────
    //  INITIAL STATE SNAPSHOT
    // ──────────────────────────────────────────────

    _saveInitialState: function () {
        this._initialTransform = {
            position: [
                this.model.position.x,
                this.model.position.y,
                this.model.position.z
            ],
            rotation: [
                this.model.rotation.x,
                this.model.rotation.y,
                this.model.rotation.z
            ],
            scale: [
                this.model.scale.x,
                this.model.scale.y,
                this.model.scale.z
            ]
        };
    },

    _cacheElements: function () {
        // Elements created in renderPanel
    },

    _bindShortcuts: function () {
        var self = this;
        this._keyHandler = function (e) {
            if (e.ctrlKey && e.shiftKey && (e.key === 'Z' || e.key === 'z')) {
                e.preventDefault();
                self.redo();
                return;
            }
            if (e.ctrlKey && e.key === 'z') {
                e.preventDefault();
                self.undo();
                return;
            }
        };
        document.addEventListener('keydown', this._keyHandler);
    },

    // ──────────────────────────────────────────────
    //  RENDER PANEL
    // ──────────────────────────────────────────────

    renderPanel: function () {
        var self = this;
        var panel = this.container;
        if (!panel) return;
        panel.innerHTML = '';

        // ── Header ──
        var header = document.createElement('div');
        header.className = 'editor-header';

        var title = document.createElement('h3');
        title.textContent = 'Ch\u1ec9nh s\u1eeda t\u00e0i nguy\u00ean 3D';
        header.appendChild(title);

        var headerActions = document.createElement('div');
        headerActions.className = 'editor-header-actions';

        var btnUndo = document.createElement('button');
        btnUndo.className = 'editor-header-btn';
        btnUndo.innerHTML = '<i class="fa-solid fa-rotate-left"></i>';
        btnUndo.title = 'Undo';
        btnUndo.addEventListener('click', function () { self.undo(); });
        headerActions.appendChild(btnUndo);

        var btnRedo = document.createElement('button');
        btnRedo.className = 'editor-header-btn';
        btnRedo.innerHTML = '<i class="fa-solid fa-rotate-right"></i>';
        btnRedo.title = 'Redo';
        btnRedo.addEventListener('click', function () { self.redo(); });
        headerActions.appendChild(btnRedo);

        var btnSave = document.createElement('button');
        btnSave.className = 'editor-header-btn';
        btnSave.innerHTML = '<i class="fa-regular fa-floppy-disk"></i>';
        btnSave.title = 'L\u01b0u';
        btnSave.addEventListener('click', function () { self.saveEditorState(); });
        headerActions.appendChild(btnSave);

        var btnExport = document.createElement('button');
        btnExport.className = 'editor-header-btn';
        btnExport.textContent = 'Xu\u1ea5t GLB';
        btnExport.title = 'Xu\u1ea5t GLB';
        btnExport.addEventListener('click', function () { self.exportGLB(); });
        headerActions.appendChild(btnExport);

        var btnToggle = document.createElement('button');
        btnToggle.className = 'editor-toggle-btn';
        btnToggle.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
        btnToggle.title = 'Thu g\u1ecdn';
        btnToggle.addEventListener('click', function () { self._toggleEditor(); });
        headerActions.appendChild(btnToggle);

        header.appendChild(headerActions);
        panel.appendChild(header);

        // ── Tab Bar ──
        var tabNames = ['Transform', 'V\u1eadt li\u1ec7u', 'Sticker', 'L\u1ecbch s\u1eed'];
        var tabBar = document.createElement('div');
        tabBar.className = 'editor-tab-bar';
        this._tabButtons = {};

        for (var ti = 0; ti < tabNames.length; ti++) {
            (function (tn) {
                var btn = document.createElement('button');
                btn.className = 'editor-tab-btn';
                if (tn === 'Transform') btn.classList.add('active');
                btn.textContent = tn;
                btn.addEventListener('click', function () { self._switchTab(tn); });
                tabBar.appendChild(btn);
                self._tabButtons[tn] = btn;
            })(tabNames[ti]);
        }
        panel.appendChild(tabBar);

        // ── Content ──
        var content = document.createElement('div');
        content.className = 'editor-content';
        this._tabPanes = {};

        // ── Tab: Transform (compact) ──
        (function () {
            var pane = document.createElement('div');
            pane.className = 'editor-tab-pane active';
            pane.dataset.pane = 'Transform';

            // Gizmo mode selector (main tool)
            var gizmoGroup = document.createElement('div');
            gizmoGroup.className = 'editor-group';
            var gizmoTitle = document.createElement('div');
            gizmoTitle.className = 'editor-group-title';
            gizmoTitle.textContent = 'Gizmo 3D';
            gizmoGroup.appendChild(gizmoTitle);

            var gizmoRow = document.createElement('div');
            gizmoRow.className = 'editor-gizmo-row';
            var gizmoModes = [
                { key: 'translate', label: 'Di chuy\u1ec3n', icon: 'arrows-up-down-left-right' },
                { key: 'rotate', label: 'Xoay', icon: 'rotate' },
                { key: 'scale', label: 'T\u1ec9 l\u1ec7', icon: 'expand' }
            ];
            for (var gi = 0; gi < gizmoModes.length; gi++) {
                (function (gm) {
                    var btn = document.createElement('button');
                    btn.className = 'editor-gizmo-btn' + (gm.key === 'translate' ? ' active' : '');
                    btn.innerHTML = '<i class="fa-solid fa-' + gm.icon + '"></i> ' + gm.label;
                    btn.addEventListener('click', function () {
                        if (window.AppState && AppState.resultScene && AppState.resultScene._setGizmoMode) {
                            AppState.resultScene._setGizmoMode(gm.key);
                        }
                        gizmoRow.querySelectorAll('.editor-gizmo-btn').forEach(function (b) {
                            b.classList.remove('active');
                        });
                        btn.classList.add('active');
                        // sync viewer gizmo bar
                        document.querySelectorAll('.gizmo-btn[data-gizmo]').forEach(function (b) {
                            b.classList.toggle('active', b.dataset.gizmo === gm.key);
                        });
                    });
                    gizmoRow.appendChild(btn);
                })(gizmoModes[gi]);
            }
            gizmoGroup.appendChild(gizmoRow);

            // Quick actions: Đặt đáy + Reset
            var quickRow = document.createElement('div');
            quickRow.className = 'editor-row';
            var qFloor = self._makeBtn('\u0110\u1eb7t \u0111\u00e1y', function () { self._floorModel(); });
            qFloor.style.flex = '1';
            var qReset = self._makeBtn('Reset', function () { self._resetModel(); });
            qReset.style.flex = '1';
            quickRow.appendChild(qFloor);
            quickRow.appendChild(qReset);
            gizmoGroup.appendChild(quickRow);
            pane.appendChild(gizmoGroup);

            // Collapsible "Tinh chỉnh"
            var collapseTrigger = document.createElement('button');
            collapseTrigger.className = 'editor-collapse-trigger';
            collapseTrigger.innerHTML = 'Tinh ch\u1ec9nh <i class="fa-solid fa-chevron-down"></i>';
            pane.appendChild(collapseTrigger);

            var collapseContent = document.createElement('div');
            collapseContent.className = 'editor-collapse-content';
            var axes = ['X', 'Y', 'Z'];

            // Rotation 15-degree row
            var rowLabel15 = document.createElement('div');
            rowLabel15.className = 'editor-label';
            rowLabel15.textContent = 'Xoay 15\u00b0:';
            collapseContent.appendChild(rowLabel15);

            var row15 = document.createElement('div');
            row15.className = 'editor-row';
            for (var a = 0; a < axes.length; a++) {
                (function (axis) {
                    var grp = document.createElement('div');
                    grp.style.cssText = 'display:flex;gap:3px;';
                    var b = self._makeBtn('+' + axis + '15', function () {
                        self._rotate(axis, 15);
                    });
                    b.style.minWidth = '44px';
                    b.style.fontSize = '12px';
                    var b2 = self._makeBtn('-' + axis + '15', function () {
                        self._rotate(axis, -15);
                    });
                    b2.style.minWidth = '44px';
                    b2.style.fontSize = '12px';
                    grp.appendChild(b);
                    grp.appendChild(b2);
                    row15.appendChild(grp);
                })(axes[a]);
            }
            collapseContent.appendChild(row15);

            // Rotation 90-degree row
            var rowLabel90 = document.createElement('div');
            rowLabel90.className = 'editor-label';
            rowLabel90.textContent = 'Xoay 90\u00b0:';
            collapseContent.appendChild(rowLabel90);

            var row90 = document.createElement('div');
            row90.className = 'editor-row';
            for (var a2 = 0; a2 < axes.length; a2++) {
                (function (axis) {
                    var grp = document.createElement('div');
                    grp.style.cssText = 'display:flex;gap:3px;';
                    var b = self._makeBtn('+' + axis + '90', function () {
                        self._rotate(axis, 90);
                    });
                    b.style.minWidth = '44px';
                    b.style.fontSize = '12px';
                    var b2 = self._makeBtn('-' + axis + '90', function () {
                        self._rotate(axis, -90);
                    });
                    b2.style.minWidth = '44px';
                    b2.style.fontSize = '12px';
                    grp.appendChild(b);
                    grp.appendChild(b2);
                    row90.appendChild(grp);
                })(axes[a2]);
            }
            collapseContent.appendChild(row90);

            // Scale slider + presets
            var scaleSep = document.createElement('div');
            scaleSep.style.cssText = 'border-top:1px solid var(--border-color);margin:8px 0;';
            collapseContent.appendChild(scaleSep);

            var scaleLabelRow = document.createElement('div');
            scaleLabelRow.className = 'editor-label';
            scaleLabelRow.textContent = 'T\u1ec9 l\u1ec7 (Scale):';
            collapseContent.appendChild(scaleLabelRow);

            var scaleSliderRow = document.createElement('div');
            scaleSliderRow.className = 'editor-row';
            self._scaleSlider = document.createElement('input');
            self._scaleSlider.type = 'range';
            self._scaleSlider.className = 'editor-slider';
            self._scaleSlider.min = '0.1';
            self._scaleSlider.max = '3.0';
            self._scaleSlider.step = '0.05';
            self._scaleSlider.value = '1.0';
            self._scaleSlider.addEventListener('input', function () {
                var v = parseFloat(self._scaleSlider.value);
                self.model.scale.set(v, v, v);
                if (self._scaleValEl) self._scaleValEl.textContent = v.toFixed(2) + 'x';
            });
            self._scaleSlider.addEventListener('change', function () {
                var v = parseFloat(self._scaleSlider.value);
                self._saveSnapshot();
                self._setStatus('T\u1ec9 l\u1ec7: ' + v.toFixed(2) + 'x');
            });
            scaleSliderRow.appendChild(self._scaleSlider);
            self._scaleValEl = document.createElement('span');
            self._scaleValEl.className = 'editor-slider-value';
            self._scaleValEl.textContent = '1.00x';
            scaleSliderRow.appendChild(self._scaleValEl);
            collapseContent.appendChild(scaleSliderRow);

            var scaleBtnRow = document.createElement('div');
            scaleBtnRow.className = 'editor-row';
            var scale05 = self._makeBtn('0.5x', function () { self._setScale(0.5); });
            var scale1 = self._makeBtn('1x', function () { self._setScale(1.0); });
            var scale2 = self._makeBtn('2x', function () { self._setScale(2.0); });
            scaleBtnRow.appendChild(scale05);
            scaleBtnRow.appendChild(scale1);
            scaleBtnRow.appendChild(scale2);
            collapseContent.appendChild(scaleBtnRow);

            pane.appendChild(collapseContent);

            // Toggle collapse
            collapseTrigger.addEventListener('click', function () {
                var isOpen = collapseContent.classList.toggle('open');
                collapseTrigger.classList.toggle('open', isOpen);
            });

            content.appendChild(pane);
            self._tabPanes['Transform'] = pane;
        })();

        // ── Tab: Vật liệu ──
        (function () {
            var pane = document.createElement('div');
            pane.className = 'editor-tab-pane';
            pane.dataset.pane = 'V\u1eadt li\u1ec7u';

            var matGroup = document.createElement('div');
            matGroup.className = 'editor-group';
            var matTitle = document.createElement('div');
            matTitle.className = 'editor-group-title';
            matTitle.textContent = 'V\u1eadt li\u1ec7u (Material)';
            matGroup.appendChild(matTitle);

            // Color
            var colorRow = document.createElement('div');
            colorRow.className = 'editor-row';
            var colorLabel = document.createElement('span');
            colorLabel.className = 'editor-label';
            colorLabel.textContent = 'M\u00e0u:';
            colorRow.appendChild(colorLabel);
            matGroup.appendChild(colorRow);

            var colorInputRow = document.createElement('div');
            colorInputRow.className = 'editor-row';
            self._matColorInput = document.createElement('input');
            self._matColorInput.type = 'color';
            self._matColorInput.className = 'editor-color';
            self._matColorInput.value = '#cccccc';
            colorInputRow.appendChild(self._matColorInput);
            self._matColorVal = document.createElement('span');
            self._matColorVal.className = 'editor-slider-value';
            self._matColorVal.textContent = '#cccccc';
            self._matColorVal.style.fontSize = '11px';
            self._matColorInput.addEventListener('change', function () {
                self._matColorVal.textContent = self._matColorInput.value;
            });
            colorInputRow.appendChild(self._matColorVal);
            matGroup.appendChild(colorInputRow);

            // Metallic
            var metalRow = document.createElement('div');
            metalRow.className = 'editor-row';
            var metalLabel = document.createElement('span');
            metalLabel.className = 'editor-label';
            metalLabel.textContent = 'Metallic:';
            metalRow.appendChild(metalLabel);
            matGroup.appendChild(metalRow);

            var metalSliderRow = document.createElement('div');
            metalSliderRow.className = 'editor-row';
            self._metalSlider = document.createElement('input');
            self._metalSlider.type = 'range';
            self._metalSlider.className = 'editor-slider';
            self._metalSlider.min = '0';
            self._metalSlider.max = '1';
            self._metalSlider.step = '0.01';
            self._metalSlider.value = '0';
            metalSliderRow.appendChild(self._metalSlider);
            self._metalValEl = document.createElement('span');
            self._metalValEl.className = 'editor-slider-value';
            self._metalValEl.textContent = '0.00';
            self._metalSlider.addEventListener('input', function () {
                self._metalValEl.textContent = parseFloat(self._metalSlider.value).toFixed(2);
            });
            metalSliderRow.appendChild(self._metalValEl);
            matGroup.appendChild(metalSliderRow);

            // Roughness
            var roughRow = document.createElement('div');
            roughRow.className = 'editor-row';
            var roughLabel = document.createElement('span');
            roughLabel.className = 'editor-label';
            roughLabel.textContent = 'Roughness:';
            roughRow.appendChild(roughLabel);
            matGroup.appendChild(roughRow);

            var roughSliderRow = document.createElement('div');
            roughSliderRow.className = 'editor-row';
            self._roughSlider = document.createElement('input');
            self._roughSlider.type = 'range';
            self._roughSlider.className = 'editor-slider';
            self._roughSlider.min = '0';
            self._roughSlider.max = '1';
            self._roughSlider.step = '0.01';
            self._roughSlider.value = '0.5';
            roughSliderRow.appendChild(self._roughSlider);
            self._roughValEl = document.createElement('span');
            self._roughValEl.className = 'editor-slider-value';
            self._roughValEl.textContent = '0.50';
            self._roughSlider.addEventListener('input', function () {
                self._roughValEl.textContent = parseFloat(self._roughSlider.value).toFixed(2);
            });
            roughSliderRow.appendChild(self._roughValEl);
            matGroup.appendChild(roughSliderRow);

            // Apply/Restore buttons
            var matBtnRow = document.createElement('div');
            matBtnRow.className = 'editor-row';
            var btnApply = self._makeBtn('\u00c1p d\u1ee5ng', function () { self._applyMaterial(); });
            var btnRestore = self._makeBtn('Kh\u00f4i ph\u1ee5c', function () { self._restoreMaterial(); });
            matBtnRow.appendChild(btnApply);
            matBtnRow.appendChild(btnRestore);
            matGroup.appendChild(matBtnRow);
            pane.appendChild(matGroup);

            content.appendChild(pane);
            self._tabPanes['V\u1eadt li\u1ec7u'] = pane;
        })();

        // ── Tab: Sticker ──
        (function () {
            var pane = document.createElement('div');
            pane.className = 'editor-tab-pane';
            pane.dataset.pane = 'Sticker';

            var stickGroup = document.createElement('div');
            stickGroup.className = 'editor-group';
            var stickTitle = document.createElement('div');
            stickTitle.className = 'editor-group-title';
            stickTitle.textContent = 'Sticker';
            stickGroup.appendChild(stickTitle);

            // Sticker mode toggle
            var modeRow = document.createElement('div');
            modeRow.className = 'editor-row';
            self._btnStickerMode = self._makeBtn('Ch\u1ebf \u0111\u1ed9: \u0110\u1eb7t sticker', function () {
                self._toggleStickerMode();
            });
            self._btnStickerMode.style.width = '100%';
            modeRow.appendChild(self._btnStickerMode);
            stickGroup.appendChild(modeRow);

            // Sticker color
            var scRow = document.createElement('div');
            scRow.className = 'editor-row';
            var scLabel = document.createElement('span');
            scLabel.className = 'editor-label';
            scLabel.textContent = 'M\u00e0u sticker:';
            scRow.appendChild(scLabel);
            stickGroup.appendChild(scRow);

            var scInputRow = document.createElement('div');
            scInputRow.className = 'editor-row';
            self._stickColorInput = document.createElement('input');
            self._stickColorInput.type = 'color';
            self._stickColorInput.className = 'editor-color';
            self._stickColorInput.value = '#ff0000';
            self._stickColorInput.addEventListener('change', function () {
                self._stickerColor = self._stickColorInput.value;
                if (self._selectedStickerIdx >= 0 && self._selectedStickerIdx < self.stickers.length) {
                    self._saveSnapshot();
                    var st = self.stickers[self._selectedStickerIdx];
                    st.color = self._stickerColor;
                    self._updateStickerMesh(st);
                    self._updateStickerList();
                    self._setStatus('Sticker color updated');
                }
            });
            scInputRow.appendChild(self._stickColorInput);
            var scVal = document.createElement('span');
            scVal.className = 'editor-slider-value';
            scVal.textContent = '#ff0000';
            scVal.style.fontSize = '11px';
            self._stickColorInput.addEventListener('change', function () {
                scVal.textContent = self._stickColorInput.value;
            });
            scInputRow.appendChild(scVal);
            stickGroup.appendChild(scInputRow);

            // Sticker size
            var ssRow = document.createElement('div');
            ssRow.className = 'editor-row';
            var ssLabel = document.createElement('span');
            ssLabel.className = 'editor-label';
            ssLabel.textContent = 'K\u00edch th\u01b0\u1edbc:';
            ssRow.appendChild(ssLabel);
            stickGroup.appendChild(ssRow);

            var ssSliderRow = document.createElement('div');
            ssSliderRow.className = 'editor-row';
            self._stickSizeSlider = document.createElement('input');
            self._stickSizeSlider.type = 'range';
            self._stickSizeSlider.className = 'editor-slider';
            self._stickSizeSlider.min = '0.02';
            self._stickSizeSlider.max = '0.2';
            self._stickSizeSlider.step = '0.005';
            self._stickSizeSlider.value = '0.08';
            self._stickSizeSlider.addEventListener('change', function () {
                self._stickerSize = parseFloat(self._stickSizeSlider.value);
                if (self._selectedStickerIdx >= 0 && self._selectedStickerIdx < self.stickers.length) {
                    self._saveSnapshot();
                    var st = self.stickers[self._selectedStickerIdx];
                    st.size = self._stickerSize;
                    self._updateStickerMesh(st);
                    self._setStatus('Sticker size: ' + st.size.toFixed(3));
                }
            });
            ssSliderRow.appendChild(self._stickSizeSlider);
            var ssVal = document.createElement('span');
            ssVal.className = 'editor-slider-value';
            ssVal.textContent = '0.080';
            self._stickSizeSlider.addEventListener('input', function () {
                ssVal.textContent = parseFloat(self._stickSizeSlider.value).toFixed(3);
            });
            ssSliderRow.appendChild(ssVal);
            stickGroup.appendChild(ssSliderRow);

            // Shape buttons
            var shapeRow = document.createElement('div');
            shapeRow.className = 'editor-row';
            var shapeLabel = document.createElement('span');
            shapeLabel.className = 'editor-label';
            shapeLabel.textContent = 'H\u00ecnh:';
            shapeRow.appendChild(shapeLabel);
            stickGroup.appendChild(shapeRow);

            var shapeBtnRow = document.createElement('div');
            shapeBtnRow.className = 'editor-row';
            self._btnShapeCircle = self._makeBtn('Tr\u00f2n', function () {
                self._stickerShape = 'circle';
                self._btnShapeCircle.classList.add('active');
                self._btnShapeSquare.classList.remove('active');
                if (self._selectedStickerIdx >= 0 && self._selectedStickerIdx < self.stickers.length) {
                    self._saveSnapshot();
                    var st = self.stickers[self._selectedStickerIdx];
                    st.shape = 'circle';
                    self._updateStickerMesh(st);
                }
            });
            self._btnShapeCircle.classList.add('active');
            shapeBtnRow.appendChild(self._btnShapeCircle);

            self._btnShapeSquare = self._makeBtn('Vu\u00f4ng', function () {
                self._stickerShape = 'square';
                self._btnShapeSquare.classList.add('active');
                self._btnShapeCircle.classList.remove('active');
                if (self._selectedStickerIdx >= 0 && self._selectedStickerIdx < self.stickers.length) {
                    self._saveSnapshot();
                    var st = self.stickers[self._selectedStickerIdx];
                    st.shape = 'square';
                    self._updateStickerMesh(st);
                }
            });
            shapeBtnRow.appendChild(self._btnShapeSquare);
            stickGroup.appendChild(shapeBtnRow);

            // Sticker count
            self._stickerCountLabel = document.createElement('div');
            self._stickerCountLabel.className = 'editor-label';
            self._stickerCountLabel.textContent = 'S\u1ed1 sticker: 0/' + self._maxStickers;
            stickGroup.appendChild(self._stickerCountLabel);

            // Sticker list
            self._stickerListDiv = document.createElement('div');
            self._stickerListDiv.className = 'editor-sticker-list';
            stickGroup.appendChild(self._stickerListDiv);

            // Delete sticker button
            var delRow = document.createElement('div');
            delRow.className = 'editor-row';
            var btnDelSticker = self._makeBtn('X\u00f3a sticker', function () { self._deleteSticker(); });
            btnDelSticker.classList.add('danger');
            delRow.appendChild(btnDelSticker);
            stickGroup.appendChild(delRow);

            pane.appendChild(stickGroup);
            content.appendChild(pane);
            self._tabPanes['Sticker'] = pane;
        })();

        // ── Tab: Lịch sử ──
        (function () {
            var pane = document.createElement('div');
            pane.className = 'editor-tab-pane';
            pane.dataset.pane = 'L\u1ecbch s\u1eed';

            var histGroup = document.createElement('div');
            histGroup.className = 'editor-group';
            var histTitle = document.createElement('div');
            histTitle.className = 'editor-group-title';
            histTitle.textContent = 'L\u1ecbch s\u1eed thao t\u00e1c';
            histGroup.appendChild(histTitle);

            var info = document.createElement('div');
            info.className = 'editor-history-info';
            info.id = 'editor-history-info';
            info.textContent = 'Undo: 0 l\u1ea7n | Redo: 0 l\u1ea7n';
            self._historyInfoEl = info;
            histGroup.appendChild(info);

            var histBtns = document.createElement('div');
            histBtns.className = 'editor-row';
            var hUndo = self._makeBtn('<i class="fa-solid fa-rotate-left"></i> Undo', function () { self.undo(); });
            var hRedo = self._makeBtn('<i class="fa-solid fa-rotate-right"></i> Redo', function () { self.redo(); });
            histBtns.appendChild(hUndo);
            histBtns.appendChild(hRedo);
            histGroup.appendChild(histBtns);

            pane.appendChild(histGroup);
            content.appendChild(pane);
            self._tabPanes['L\u1ecbch s\u1eed'] = pane;
        })();

        panel.appendChild(content);

        // ── Status ──
        this._statusEl = document.createElement('div');
        this._statusEl.className = 'editor-status';
        panel.appendChild(this._statusEl);
    },

    _switchTab: function (name) {
        for (var key in this._tabButtons) {
            if (this._tabButtons.hasOwnProperty(key)) {
                this._tabButtons[key].classList.toggle('active', key === name);
            }
        }
        for (var key in this._tabPanes) {
            if (this._tabPanes.hasOwnProperty(key)) {
                this._tabPanes[key].classList.toggle('active', key === name);
            }
        }
    },

    _toggleEditor: function () {
        var w = window.innerWidth;
        if (w >= 1500) {
            // Desktop: collapse/expand panel
            var layout = document.getElementById('result-layout');
            if (layout) {
                layout.classList.toggle('editor-collapsed');
                var collapsed = layout.classList.contains('editor-collapsed');
                var btn = this.container.querySelector('.editor-toggle-btn i');
                if (btn) {
                    btn.className = collapsed ? 'fa-solid fa-chevron-left' : 'fa-solid fa-chevron-right';
                }
            }
        } else {
            // Tablet/mobile: close drawer
            this.closeDrawer();
        }
    },

    openDrawer: function () {
        this.container.classList.add('open');
        var backdrop = document.getElementById('editor-backdrop');
        if (backdrop) backdrop.classList.add('active');
        // Signal viewer to resize after transition
        var self = this;
        setTimeout(function () {
            if (self.controls) self.controls.update();
            if (window.onViewerResize) window.onViewerResize();
        }, 350);
    },

    closeDrawer: function () {
        this.container.classList.remove('open');
        var backdrop = document.getElementById('editor-backdrop');
        if (backdrop) backdrop.classList.remove('active');
    },

    _createGroupLabel: function (text) {
        var h = document.createElement('div');
        h.className = 'editor-group';
        h.textContent = '\u2550\u2550\u2550 ' + text + ' \u2550\u2550\u2550';
        return h;
    },

    _makeBtn: function (label, cb) {
        var btn = document.createElement('button');
        btn.className = 'editor-btn';
        btn.innerHTML = label;
        btn.addEventListener('click', cb);
        return btn;
    },

    // ──────────────────────────────────────────────
    //  CLICK HANDLERS (canvas interactions)
    // ──────────────────────────────────────────────

    _initClickHandlers: function () {
        var self = this;
        var canvas = this.controls ? this.controls.domElement : null;
        if (!canvas) return;

        // Track pointer down to detect drag vs click
        this._pdHandler = function (e) {
            self._pointerDownPos.x = e.clientX;
            self._pointerDownPos.y = e.clientY;
        };
        canvas.addEventListener('pointerdown', this._pdHandler);

        this._clickHandler = function (e) {
            // Guard: ignore if this was a drag (orbit/pan)
            var dx = e.clientX - self._pointerDownPos.x;
            var dy = e.clientY - self._pointerDownPos.y;
            if (dx * dx + dy * dy > 16) return;

            var rect = canvas.getBoundingClientRect();
            self._mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
            self._mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

            if (self._stickerMode) {
                self._placeSticker();
            } else {
                self._selectStickerFromClick();
            }
        };
        canvas.addEventListener('click', this._clickHandler);
    },

    // ──────────────────────────────────────────────
    //  TRANSFORM OPERATIONS
    // ──────────────────────────────────────────────

    _rotate: function (axis, degrees) {
        this._saveSnapshot();
        var rad = degrees * Math.PI / 180;
        if (axis === 'X') this.model.rotation.x += rad;
        else if (axis === 'Y') this.model.rotation.y += rad;
        else if (axis === 'Z') this.model.rotation.z += rad;
        this.model.updateMatrixWorld(true);
        this._setStatus('Rotated ' + axis + ' ' + degrees + '\u00b0');
    },

    _setScale: function (factor) {
        this._saveSnapshot();
        this.model.scale.set(factor, factor, factor);
        if (this._scaleSlider) this._scaleSlider.value = String(factor);
        if (this._scaleValEl) this._scaleValEl.textContent = factor.toFixed(2) + 'x';
        this._setStatus('Scale: ' + factor + 'x');
    },

    _floorModel: function () {
        this._saveSnapshot();
        this.model.updateMatrixWorld(true);
        var box = new THREE.Box3().setFromObject(this.model);
        var minY = box.min.y;
        this.model.position.y += (-0.5 - minY);
        this.model.updateMatrixWorld(true);
        this._setStatus('\u0110\u00e3 \u0111\u1eb7t \u0111\u00e1y ch\u1ea1m s\u00e0n (y=-0.5)');
    },

    _centerModel: function () {
        this._saveSnapshot();
        var box = new THREE.Box3().setFromObject(this.model);
        var center = box.getCenter(new THREE.Vector3());
        this.model.position.x -= center.x;
        this.model.position.y -= center.y;
        this.model.position.z -= center.z;
        this.model.updateMatrixWorld(true);
        this._setStatus('\u0110\u00e3 v\u1ec1 g\u1ed1c t\u1ecda \u0111\u1ed9');
    },

    _resetModel: function () {
        this._saveSnapshot();
        var t = this._initialTransform;
        this.model.position.set(t.position[0], t.position[1], t.position[2]);
        this.model.rotation.set(t.rotation[0], t.rotation[1], t.rotation[2]);
        this.model.scale.set(t.scale[0], t.scale[1], t.scale[2]);
        if (this._scaleSlider) this._scaleSlider.value = '1.0';
        this.model.updateMatrixWorld(true);
        this._setStatus('Reset to initial state');
    },

    // ──────────────────────────────────────────────
    //  MATERIAL
    // ──────────────────────────────────────────────

    _saveOriginalMaterials: function () {
        if (this._originalMaterials.size > 0) return;
        var self = this;
        this.model.traverse(function (child) {
            if (child.isMesh && child.material) {
                if (Array.isArray(child.material)) {
                    var clones = [];
                    for (var i = 0; i < child.material.length; i++) {
                        clones.push(child.material[i].clone());
                    }
                    self._originalMaterials.set(child.uuid, clones);
                } else {
                    self._originalMaterials.set(child.uuid, child.material.clone());
                }
            }
        });
    },

    _applyMaterial: function () {
        this._saveSnapshot();
        this._saveOriginalMaterials();

        var colorStr = this._matColorInput.value;
        var metallic = parseFloat(this._metalSlider.value);
        var roughness = parseFloat(this._roughSlider.value);
        var color = new THREE.Color(colorStr);

        var self = this;
        this.model.traverse(function (child) {
            if (child.isMesh && child.material) {
                var mats = Array.isArray(child.material) ? child.material : [child.material];
                for (var i = 0; i < mats.length; i++) {
                    var m = mats[i];
                    if (m.color) m.color.copy(color);
                    if (m.metalness !== undefined) m.metalness = metallic;
                    if (m.roughness !== undefined) m.roughness = roughness;
                    m.needsUpdate = true;
                }
            }
        });

        this._materialApplied = true;
        this._currentColor = colorStr;
        this._currentMetallic = metallic;
        this._currentRoughness = roughness;
        this._setStatus('\u0110\u00e3 \u00e1p d\u1ee5ng v\u1eadt li\u1ec7u m\u1edbi');
    },

    _restoreMaterial: function () {
        if (this._originalMaterials.size === 0) {
            this._setStatus('Kh\u00f4ng c\u00f3 v\u1eadt li\u1ec7u g\u1ed1c \u0111\u1ec3 kh\u00f4i ph\u1ee5c', true);
            return;
        }
        this._saveSnapshot();
        var self = this;
        this.model.traverse(function (child) {
            if (child.isMesh && child.material) {
                var orig = self._originalMaterials.get(child.uuid);
                if (orig) {
                    child.material = orig;
                }
            }
        });
        this._materialApplied = false;
        this._setStatus('\u0110\u00e3 kh\u00f4i ph\u1ee5c v\u1eadt li\u1ec7u g\u1ed1c');
    },

    // ──────────────────────────────────────────────
    //  STICKERS
    // ──────────────────────────────────────────────

    _toggleStickerMode: function () {
        this._stickerMode = !this._stickerMode;
        this._btnStickerMode.textContent = this._stickerMode
            ? 'Ch\u1ebf \u0111\u1ed9: \u0110\u1eb7t sticker (B\u1eadt)'
            : 'Ch\u1ebf \u0111\u1ed9: \u0110\u1eb7t sticker';
        this._btnStickerMode.classList.toggle('active', this._stickerMode);
        if (this._stickerMode) {
            this.controls.enableRotate = false;
            this._setStatus('Click v\u00e0o model \u0111\u1ec3 \u0111\u1eb7t sticker');
        } else {
            this.controls.enableRotate = true;
            this._setStatus('Sticker mode off');
        }
    },

    _placeSticker: function () {
        if (this.stickers.length >= this._maxStickers) {
            this._setStatus('\u0110\u00e3 \u0111\u1ea1t gi\u1edbi h\u1ea1n ' + this._maxStickers + ' sticker', true);
            return;
        }

        this._raycaster.setFromCamera(this._mouse, this.camera);
        var meshes = [];
        this.model.traverse(function (child) {
            if (child.isMesh) meshes.push(child);
        });
        if (meshes.length === 0) return;

        var intersects = this._raycaster.intersectObjects(meshes, false);
        if (intersects.length === 0) return;

        var hit = intersects[0];
        var point = hit.point.clone();
        var normal = hit.face.normal.clone();
        var objMat = new THREE.Matrix4().extractRotation(hit.object.matrixWorld);
        normal.applyMatrix4(objMat).normalize();

        this._saveSnapshot();
        var sticker = this._createSticker(
            point, normal,
            this._stickerColor,
            this._stickerSize,
            this._stickerShape
        );
        this.stickers.push(sticker);
        this._updateStickerList();
        this._setStatus('Sticker #' + (this.stickers.length) + ' placed');
    },

    _createStickerTexture: function (colorHex, shape) {
        var canvas = document.createElement('canvas');
        var res = 64;
        canvas.width = res;
        canvas.height = res;
        var ctx = canvas.getContext('2d');
        var half = res / 2;
        var r = half - 2;

        ctx.clearRect(0, 0, res, res);

        if (shape === 'circle') {
            ctx.beginPath();
            ctx.arc(half, half, r, 0, Math.PI * 2);
            ctx.closePath();
        } else {
            ctx.beginPath();
            ctx.rect(2, 2, res - 4, res - 4);
            ctx.closePath();
        }

        ctx.fillStyle = colorHex;
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        var texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        return texture;
    },

    _createSticker: function (position, normal, color, size, shape) {
        var texture = this._createStickerTexture(color, shape);
        var material = new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            depthTest: true,
            depthWrite: false,
            sizeAttenuation: true
        });
        var sprite = new THREE.Sprite(material);
        sprite.position.copy(position);
        sprite.scale.set(size, size, 1);
        sprite.userData.isSticker = true;

        this.scene.add(sprite);

        this._stickerIdCounter++;
        return {
            id: 'sticker_' + this._stickerIdCounter,
            position: [position.x, position.y, position.z],
            normal: [normal.x, normal.y, normal.z],
            color: color,
            size: size,
            shape: shape,
            mesh: sprite
        };
    },

    _updateStickerMesh: function (sticker) {
        var tex = this._createStickerTexture(sticker.color, sticker.shape);
        sticker.mesh.material.map = tex;
        sticker.mesh.material.needsUpdate = true;
        sticker.mesh.scale.set(sticker.size, sticker.size, 1);
    },

    _selectStickerFromClick: function () {
        if (this.stickers.length === 0) {
            this._deselectSticker();
            return;
        }

        this._raycaster.setFromCamera(this._mouse, this.camera);

        // Manual distance-based hit test for sprites
        var closestIdx = -1;
        var closestDist = Infinity;

        for (var i = 0; i < this.stickers.length; i++) {
            var sp = this.stickers[i].mesh;
            var d = this._raycaster.ray.distanceToPoint(sp.position);
            // Use a threshold based on the sprite's world-space size
            var threshold = sp.scale.x * 1.5;
            if (d < threshold && d < closestDist) {
                closestDist = d;
                closestIdx = i;
            }
        }

        if (closestIdx >= 0) {
            this._selectedStickerIdx = closestIdx;
            this._highlightSelectedSticker();
            this._updateStickerList();
            var st = this.stickers[closestIdx];
            this._stickColorInput.value = st.color;
            this._stickSizeSlider.value = String(st.size);
            this._stickerShape = st.shape;
            this._btnShapeCircle.classList.toggle('active', st.shape === 'circle');
            this._btnShapeSquare.classList.toggle('active', st.shape === 'square');
            this._setStatus('Selected sticker #' + (closestIdx + 1));
        } else {
            this._deselectSticker();
        }
    },

    _deselectSticker: function () {
        if (this._selectedStickerIdx >= 0) {
            this._selectedStickerIdx = -1;
            this._updateStickerList();
        }
    },

    _highlightSelectedSticker: function () {
        for (var i = 0; i < this.stickers.length; i++) {
            var st = this.stickers[i];
            st.mesh.material.opacity = (i === this._selectedStickerIdx) ? 1.0 : 0.6;
            st.mesh.material.needsUpdate = true;
        }
    },

    _deleteSticker: function () {
        if (this._selectedStickerIdx < 0 || this._selectedStickerIdx >= this.stickers.length) {
            this._setStatus('No sticker selected', true);
            return;
        }
        this._saveSnapshot();
        var st = this.stickers[this._selectedStickerIdx];
        this.scene.remove(st.mesh);
        st.mesh.material.map.dispose();
        st.mesh.material.dispose();
        this.stickers.splice(this._selectedStickerIdx, 1);
        this._selectedStickerIdx = -1;
        this._updateStickerList();
        this._setStatus('Sticker deleted');
    },

    _updateStickerList: function () {
        var div = this._stickerListDiv;
        if (!div) return;
        div.innerHTML = '';
        this._stickerCountLabel.textContent = 'S\u1ed1 sticker: ' + this.stickers.length + '/' + this._maxStickers;

        for (var i = 0; i < this.stickers.length; i++) {
            var item = document.createElement('div');
            item.className = 'editor-sticker-item';
            if (i === this._selectedStickerIdx) {
                item.classList.add('selected');
            }
            item.textContent = '\u25bc Sticker ' + (i + 1) + ' (' + this.stickers[i].shape + ')';
            (function (idx, self) {
                item.addEventListener('click', function () {
                    self._selectedStickerIdx = idx;
                    self._highlightSelectedSticker();
                    self._updateStickerList();
                    var st = self.stickers[idx];
                    self._stickColorInput.value = st.color;
                    self._stickSizeSlider.value = String(st.size);
                    self._stickerShape = st.shape;
                    self._btnShapeCircle.classList.toggle('active', st.shape === 'circle');
                    self._btnShapeSquare.classList.toggle('active', st.shape === 'square');
                });
            })(i, this);
            div.appendChild(item);
        }
    },

    // ──────────────────────────────────────────────
    //  UNDO / REDO
    // ──────────────────────────────────────────────

    _getCurrentSnapshot: function () {
        var pos = this.model.position;
        var rot = this.model.rotation;
        var sc = this.model.scale;

        var stickerData = [];
        for (var i = 0; i < this.stickers.length; i++) {
            var s = this.stickers[i];
            stickerData.push({
                id: s.id,
                position: s.position,
                normal: s.normal,
                color: s.color,
                size: s.size,
                shape: s.shape
            });
        }

        return {
            transform: {
                position: [pos.x, pos.y, pos.z],
                rotation: [rot.x, rot.y, rot.z],
                scale: [sc.x, sc.y, sc.z]
            },
            material: {
                color: this._currentColor,
                metallic: this._currentMetallic,
                roughness: this._currentRoughness,
                applied: this._materialApplied
            },
            stickers: stickerData
        };
    },

    _saveSnapshot: function () {
        if (this._snapshotInProgress) return;
        var snap = this._getCurrentSnapshot();
        this._undoStack.push(snap);
        if (this._undoStack.length > this._MAX_UNDO) {
            this._undoStack.shift();
        }
        this._redoStack = [];
    },

    undo: function () {
        if (this._undoStack.length === 0) {
            this._setStatus('Nothing to undo', true);
            return;
        }
        this._snapshotInProgress = true;
        var currentSnap = this._getCurrentSnapshot();
        this._redoStack.push(currentSnap);

        var snap = this._undoStack.pop();
        this._restoreSnapshot(snap);
        this._snapshotInProgress = false;
        this._setStatus('Undo');
        this._updateHistoryInfo();
    },

    redo: function () {
        if (this._redoStack.length === 0) {
            this._setStatus('Nothing to redo', true);
            return;
        }
        this._snapshotInProgress = true;
        var currentSnap = this._getCurrentSnapshot();
        this._undoStack.push(currentSnap);

        var snap = this._redoStack.pop();
        this._restoreSnapshot(snap);
        this._snapshotInProgress = false;
        this._setStatus('Redo');
        this._updateHistoryInfo();
    },

    _updateHistoryInfo: function () {
        if (this._historyInfoEl) {
            this._historyInfoEl.textContent = 'Undo: ' + this._undoStack.length + ' l\u1ea7n | Redo: ' + this._redoStack.length + ' l\u1ea7n';
        }
    },

    _restoreSnapshot: function (snap) {
        // Transform
        var t = snap.transform;
        this.model.position.set(t.position[0], t.position[1], t.position[2]);
        this.model.rotation.set(t.rotation[0], t.rotation[1], t.rotation[2]);
        this.model.scale.set(t.scale[0], t.scale[1], t.scale[2]);
        if (this._scaleSlider) {
            this._scaleSlider.value = String(t.scale[0]);
        }
        if (this._scaleValEl) {
            this._scaleValEl.textContent = parseFloat(t.scale[0]).toFixed(2) + 'x';
        }
        this.model.updateMatrixWorld(true);

        // Material
        var m = snap.material;
        this._currentColor = m.color;
        this._currentMetallic = m.metallic;
        this._currentRoughness = m.roughness;
        this._materialApplied = m.applied;

        if (this._matColorInput) this._matColorInput.value = m.color;
        if (this._metalSlider) this._metalSlider.value = String(m.metallic);
        if (this._roughSlider) this._roughSlider.value = String(m.roughness);

        if (m.applied) {
            var color = new THREE.Color(m.color);
            var self = this;
            this.model.traverse(function (child) {
                if (child.isMesh && child.material) {
                    var mats = Array.isArray(child.material) ? child.material : [child.material];
                    for (var i = 0; i < mats.length; i++) {
                        var mt = mats[i];
                        if (mt.color) mt.color.copy(color);
                        if (mt.metalness !== undefined) mt.metalness = m.metallic;
                        if (mt.roughness !== undefined) mt.roughness = m.roughness;
                        mt.needsUpdate = true;
                    }
                }
            });
        } else if (this._originalMaterials.size > 0) {
            // Restore originals when snapshot has material un-applied
            var self = this;
            this.model.traverse(function (child) {
                if (child.isMesh && child.material) {
                    var orig = self._originalMaterials.get(child.uuid);
                    if (orig) {
                        child.material = orig;
                    }
                }
            });
        }

        // Stickers — remove old
        for (var i = 0; i < this.stickers.length; i++) {
            this.scene.remove(this.stickers[i].mesh);
            this.stickers[i].mesh.material.map.dispose();
            this.stickers[i].mesh.material.dispose();
        }
        this.stickers = [];

        // Recreate from snapshot data
        for (var j = 0; j < snap.stickers.length; j++) {
            var sd = snap.stickers[j];
            var pos = new THREE.Vector3(sd.position[0], sd.position[1], sd.position[2]);
            var nrm = new THREE.Vector3(sd.normal[0], sd.normal[1], sd.normal[2]);
            // Parse id number for counter tracking
            var idNum = parseInt(sd.id.replace('sticker_', ''), 10);
            if (idNum > this._stickerIdCounter) this._stickerIdCounter = idNum;

            var sticker = this._createSticker(pos, nrm, sd.color, sd.size, sd.shape);
            sticker.id = sd.id;
            this.stickers.push(sticker);
        }
        this._selectedStickerIdx = -1;
        this._updateStickerList();
        this._updateHistoryInfo();
    },

    // ──────────────────────────────────────────────
    //  SAVE / LOAD STATE  (persistent server-side)
    // ──────────────────────────────────────────────

    _getEditorState: function () {
        var snap = this._getCurrentSnapshot();
        return {
            transform: snap.transform,
            material: snap.material,
            stickers: snap.stickers
        };
    },

    saveEditorState: function () {
        var self = this;
        var state = this._getEditorState();
        var url = '/api/assets/' + this.assetId + '/editor-save';

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(state)
        })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.success) {
                self._setStatus('Editor state saved successfully');
            } else {
                self._setStatus('Save failed: ' + (data.message || 'Unknown error'), true);
            }
        })
        .catch(function (err) {
            self._setStatus('Save error: ' + err.message, true);
        });
    },

    loadEditorState: function () {
        var self = this;
        var url = '/api/assets/' + this.assetId + '/editor-load';

        fetch(url)
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.success && data.state) {
                self._snapshotInProgress = true;
                self._restoreSnapshot(data.state);
                self._snapshotInProgress = false;
                self._undoStack = [];
                self._redoStack = [];
                self._setStatus('Editor state restored');
            }
        })
        .catch(function () {
            // No saved state exists — this is normal
        });
    },

    exportGLB: function () {
        var self = this;
        if (typeof THREE.GLTFExporter === 'undefined') {
            self._setStatus('Export requires GLTFExporter library', true);
            return;
        }

        var exporter = new THREE.GLTFExporter();
        exporter.parse(
            this.scene,
            function (gltf) {
                var output = JSON.stringify(gltf, null, 2);
                var base64 = btoa(output);

                fetch('/api/assets/' + self.assetId + '/export-edited', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data: base64, format: 'gltf' })
                })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (d.success) {
                        self._setStatus('GLB exported successfully');
                    } else {
                        self._setStatus('Export failed: ' + (d.message || 'Unknown'), true);
                    }
                })
                .catch(function (err) {
                    self._setStatus('Export error: ' + err.message, true);
                });
            },
            function (error) {
                self._setStatus('Export parse error: ' + error.message, true);
            },
            { binary: true, trs: true, onlyVisible: true }
        );
    },

    // ──────────────────────────────────────────────
    //  STATUS
    // ──────────────────────────────────────────────

    _setStatus: function (msg, isError) {
        if (!this._statusEl) return;
        this._statusEl.textContent = msg;
        this._statusEl.style.color = isError ? '#ff6b6b' : '#4ecdc4';
        if (this._statusTimer) clearTimeout(this._statusTimer);
        var self = this;
        this._statusTimer = setTimeout(function () {
            self._statusEl.textContent = '';
        }, 3000);
    }
};
