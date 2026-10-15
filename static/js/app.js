/**
 * 3DGame Asset Generator - Core Client Application JavaScript
 * Single Page Application (SPA) Controller & Three.js 3D Viewers Integration
 */

// Global Application State
const AppState = {
    currentView: 'home',
    activeAssetId: null,
    activeAssetData: null,
    
    // Three.js Instances
    heroScene: { scene: null, camera: null, renderer: null, mesh: null, animationId: null },
    resultScene: { scene: null, camera: null, renderer: null, controls: null, model: null, animationId: null, autoRotate: true },
    classroomScene: { scene: null, camera: null, renderer: null, controls: null, deskModel: null, activeAssetModel: null, animationId: null }
};

// Main Initialization
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initHeroCanvas();
    initUploadHandler();
    initResultToolbar();
    initClassroomControls();
    
    // Load initial views if requested
    const hash = window.location.hash.replace('#', '');
    if (hash && ['home', 'upload', 'library', 'templates', 'classroom', 'about'].includes(hash)) {
        switchView(hash);
    } else {
        switchView('home');
    }
});

// ==========================================
// 1. VIEW NAVIGATION & TRANSITIONS
// ==========================================
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-menu .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const viewId = item.getAttribute('data-view');
            switchView(viewId);
        });
    });
}

function switchView(viewId) {
    if (AppState.currentView === viewId && viewId !== 'home') return;
    
    // Update active nav state
    document.querySelectorAll('.nav-menu .nav-item').forEach(item => {
        if (item.getAttribute('data-view') === viewId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Hide all sections with transition
    const oldSection = document.getElementById(`view-${AppState.currentView}`);
    const newSection = document.getElementById(`view-${viewId}`);
    
    if (oldSection) {
        oldSection.classList.remove('active');
    }
    
    // Clean up timers/renders to optimize performance
    stopViewRenders(AppState.currentView);
    
    // Update state
    AppState.currentView = viewId;
    window.location.hash = viewId;
    
    // Show new section
    if (newSection) {
        newSection.classList.add('active');
        // Trigger specific view initializations
        triggerViewLoad(viewId);
    }
}

function stopViewRenders(viewId) {
    if (viewId === 'home' && AppState.heroScene.animationId) {
        cancelAnimationFrame(AppState.heroScene.animationId);
        AppState.heroScene.animationId = null;
    }
    if (viewId === 'result' && AppState.resultScene.animationId) {
        cancelAnimationFrame(AppState.resultScene.animationId);
        AppState.resultScene.animationId = null;
    }
    if (viewId === 'classroom' && AppState.classroomScene.animationId) {
        cancelAnimationFrame(AppState.classroomScene.animationId);
        AppState.classroomScene.animationId = null;
    }
}

function triggerViewLoad(viewId) {
    setTimeout(() => {
        if (viewId === 'home') {
            initHeroCanvas();
        } else if (viewId === 'library') {
            loadLibrary();
        } else if (viewId === 'templates') {
            loadTemplates();
        } else if (viewId === 'classroom') {
            initClassroomViewer();
            loadClassroomAssets();
        } else if (viewId === 'result' && AppState.activeAssetData) {
            initResultViewer();
        }
    }, 100);
}

// Handle window resizing for all active Three.js viewports
function resizeResultViewer() {
    if (AppState.resultScene && AppState.resultScene.renderer) {
        var container = document.getElementById('result-canvas-container');
        if (container && container.clientWidth > 0 && container.clientHeight > 0) {
            AppState.resultScene.camera.aspect = container.clientWidth / container.clientHeight;
            AppState.resultScene.camera.updateProjectionMatrix();
            AppState.resultScene.renderer.setSize(container.clientWidth, container.clientHeight);
        }
    }
}

window.onViewerResize = resizeResultViewer;

window.addEventListener('resize', function () {
    if (AppState.currentView === 'home' && AppState.heroScene.renderer) {
        var container = document.getElementById('hero-canvas-container');
        if (container) {
            AppState.heroScene.camera.aspect = container.clientWidth / container.clientHeight;
            AppState.heroScene.camera.updateProjectionMatrix();
            AppState.heroScene.renderer.setSize(container.clientWidth, container.clientHeight);
        }
    }
    resizeResultViewer();
    if (AppState.currentView === 'classroom' && AppState.classroomScene.renderer) {
        var container = document.getElementById('classroom-canvas-container');
        if (container) {
            AppState.classroomScene.camera.aspect = container.clientWidth / container.clientHeight;
            AppState.classroomScene.camera.updateProjectionMatrix();
            AppState.classroomScene.renderer.setSize(container.clientWidth, container.clientHeight);
        }
    }
});

// ResizeObserver for result canvas container (detects layout changes without window resize)
if (typeof ResizeObserver !== 'undefined') {
    var _resultResizeObserver = new ResizeObserver(function () {
        resizeResultViewer();
    });
    var _observeResultContainer = function () {
        var c = document.getElementById('result-canvas-container');
        if (c) {
            _resultResizeObserver.observe(c);
            if (c.parentElement) {
                _resultResizeObserver.observe(c.parentElement);
            }
        }
    };
    // Observe after DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _observeResultContainer);
    } else {
        _observeResultContainer();
    }
}

// ==========================================
// 2. HERO PAGE 3D ROTATING SHAPE
// ==========================================
function initHeroCanvas() {
    const container = document.getElementById('hero-canvas-container');
    if (!container || AppState.heroScene.animationId) return;
    
    // Clear any previous canvas
    container.innerHTML = '';
    
    // Setup Scene
    const scene = new THREE.Scene();
    AppState.heroScene.scene = scene;
    
    // Setup Camera
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.z = 6;
    AppState.heroScene.camera = camera;
    
    // Setup Renderer
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);
    AppState.heroScene.renderer = renderer;
    
    // Add Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    
    const dirLight1 = new THREE.DirectionalLight(0x3b82f6, 1.2);
    dirLight1.position.set(2, 4, 3);
    scene.add(dirLight1);
    
    const dirLight2 = new THREE.DirectionalLight(0x8b5cf6, 1.2);
    dirLight2.position.set(-2, -4, -3);
    scene.add(dirLight2);
    
    // Create a beautiful complex geometric shape representing AI computation
    const geometry = new THREE.TorusKnotGeometry(1.2, 0.4, 150, 16);
    const material = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        roughness: 0.1,
        metalness: 0.9,
        wireframe: false
    });
    
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);
    AppState.heroScene.mesh = mesh;
    
    // Animation Loop
    function animate() {
        if (AppState.currentView !== 'home') return;
        AppState.heroScene.animationId = requestAnimationFrame(animate);
        
        // Complex smooth rotation
        mesh.rotation.x += 0.005;
        mesh.rotation.y += 0.007;
        mesh.rotation.z += 0.002;
        
        // Gentle floating effect
        mesh.position.y = Math.sin(Date.now() * 0.001) * 0.15;
        
        renderer.render(scene, camera);
    }
    
    animate();
}


// ==========================================
// 3. UPLOAD PAGE DRAG & DROP & AJAX SUBMIT
// ==========================================
function initUploadHandler() {
    const dragDropArea = document.getElementById('drag-drop-area');
    const fileInput = document.getElementById('file-input');
    const nameInput = document.getElementById('asset-name-input');
    const btnSubmitGenerate = document.getElementById('btn-submit-generate');
    const uploadForm = document.getElementById('upload-form');
    const slotsGrid = document.getElementById('image-slots-grid');
    const slotsContainer = document.getElementById('slots-container');
    const slotCountEl = document.getElementById('slot-count');
    const btnClearAll = document.getElementById('btn-clear-all');

    if (!dragDropArea) return;

    const MAX_IMAGES = 6;
    const ANGLE_LABELS = ['Trước', 'Sau', 'Trái', 'Phải', 'Trên', 'Dưới'];
    let selectedFiles = [];

    function renderSlots() {
        slotsContainer.innerHTML = '';
        slotCountEl.textContent = selectedFiles.length;

        selectedFiles.forEach((file, idx) => {
            const slot = document.createElement('div');
            slot.className = 'image-slot filled' + (idx === 0 ? ' is-primary' : '');
            const url = URL.createObjectURL(file);
            slot.innerHTML = `
                <img src="${url}" class="slot-img" alt="View ${idx + 1}">
                <div class="angle-tooltip">${ANGLE_LABELS[idx] || 'Góc ' + (idx + 1)}</div>
                <button type="button" class="slot-remove" data-idx="${idx}" title="Xóa ảnh này">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            `;
            slotsContainer.appendChild(slot);
        });

        // Add empty slots up to MAX_IMAGES
        for (let i = selectedFiles.length; i < MAX_IMAGES; i++) {
            const slot = document.createElement('div');
            slot.className = 'image-slot';
            slot.innerHTML = `
                <div class="slot-add-btn">
                    <i class="fa-solid fa-plus"></i>
                    <span>${ANGLE_LABELS[i] || ''}</span>
                </div>
            `;
            slotsContainer.appendChild(slot);
        }

        // Bind remove buttons
        slotsContainer.querySelectorAll('.slot-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.dataset.idx);
                selectedFiles.splice(idx, 1);
                syncFileInput();
                renderSlots();
            });
        });

        // Bind empty slots to add more
        slotsContainer.querySelectorAll('.image-slot:not(.filled)').forEach((slot, i) => {
            slot.addEventListener('click', () => {
                if (selectedFiles.length < MAX_IMAGES) {
                    fileInput.click();
                }
            });
        });

        btnSubmitGenerate.disabled = selectedFiles.length === 0;
        dragDropArea.style.display = selectedFiles.length === 0 ? 'block' : 'none';
        slotsGrid.style.display = selectedFiles.length > 0 ? 'block' : 'none';
    }

    function syncFileInput() {
        const dt = new DataTransfer();
        selectedFiles.forEach(f => dt.items.add(f));
        fileInput.files = dt.files;
    }

    function addFiles(fileList) {
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
        for (const file of fileList) {
            if (!validTypes.includes(file.type)) {
                alert(`"${file.name}" không hợp lệ! Chỉ chấp nhận JPG, PNG.`);
                continue;
            }
            if (selectedFiles.length >= MAX_IMAGES) {
                alert('Tối đa 6 ảnh!');
                break;
            }
            selectedFiles.push(file);
        }
        syncFileInput();
        renderSlots();

        if (!nameInput.value.trim() && selectedFiles.length > 0) {
            const cleanName = selectedFiles[0].name.split('.')[0].replace(/[_-]/g, ' ');
            nameInput.value = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
        }
    }

    // Click area to select files
    dragDropArea.addEventListener('click', () => fileInput.click());

    // Drag events
    ['dragenter', 'dragover'].forEach(eventName => {
        dragDropArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            dragDropArea.classList.add('active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dragDropArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            dragDropArea.classList.remove('active');
        }, false);
    });

    // Handle drop
    dragDropArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files.length > 0) addFiles(dt.files);
    });

    // Handle file picker selection
    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) addFiles(fileInput.files);
        fileInput.value = '';
    });

    // Clear all
    btnClearAll.addEventListener('click', () => {
        selectedFiles = [];
        syncFileInput();
        nameInput.value = '';
        renderSlots();
    });

    // Form submission
    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();

        if (selectedFiles.length === 0) {
            alert('Vui lòng chọn ít nhất 1 hình ảnh!');
            return;
        }

        const assetName = nameInput.value.trim();
        const assetStyle = document.getElementById('asset-style-input').value;

        // Create FormData with all files
        const formData = new FormData();
        selectedFiles.forEach(f => formData.append('files', f));
        formData.append('name', assetName);
        formData.append('style', assetStyle);

        // Switch to AI Processing View
        switchView('processing');
        runAIProcessingPipeline(formData);
    });
    
}


// ==========================================
// 4. AI PROCESSING WORKFLOW PIPELINE
// ==========================================
async function runAIProcessingPipeline(formData) {
    const bar = document.getElementById('processing-bar');
    const percentageText = document.getElementById('processing-percentage');
    
    // Reset stepper display to pending
    for (let i = 1; i <= 7; i++) {
        const card = document.getElementById(`step-${i}`);
        card.className = 'step-card pending';
        document.getElementById(`step-status-${i}`).innerHTML = '<span class="step-wait"><i class="fa-regular fa-clock"></i></span>';
    }
    bar.style.width = '0%';
    percentageText.textContent = 'Tiến độ: 0%';
    
    let assetId = null;
    
    try {
        // --- STEP 1: Uploading Image ---
        setStepState(1, 'active');
        updateProgress(10);
        
        const uploadRes = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        if (!uploadRes.ok) {
            const text = await uploadRes.text();
            let msg = 'Lỗi tải ảnh lên server.';
            try { const j = JSON.parse(text); if (j.error) msg = j.error; } catch(e) {}
            throw new Error(msg);
        }
        const uploadData = await uploadRes.json();
        
        assetId = uploadData.asset_id;
        setStepState(1, 'completed');
        updateProgress(15);
        
        // --- STEP 2: Removing Background (AI Rembg) ---
        setStepState(2, 'active');
        updateProgress(25);
        
        const bgRes = await fetch('/api/bg-remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asset_id: assetId })
        });
        if (!bgRes.ok) {
            const text = await bgRes.text();
            let msg = 'Lỗi tách nền hình ảnh AI.';
            try { const j = JSON.parse(text); if (j.error) msg = j.error; } catch(e) {}
            throw new Error(msg);
        }
        const bgData = await bgRes.json();
        
        setStepState(2, 'completed');
        updateProgress(40);
        
        // --- STEP 3: Detecting Object ---
        setStepState(3, 'active');
        updateProgress(45);
        await sleep(1000); // Artificial minor delay for fluid visualization
        setStepState(3, 'completed');
        updateProgress(55);
        
        // --- STEP 4: Generating Geometry (TripoSR / Smart Reconstruction Engine) ---
        setStepState(4, 'active');
        updateProgress(65);
        
        const generateRes = await fetch('/api/generate-3d', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asset_id: assetId })
        });
        if (!generateRes.ok) {
            const text = await generateRes.text();
            let msg = 'Lỗi tính toán sinh mô hình 3D.';
            try { const j = JSON.parse(text); if (j.error) msg = j.error; } catch(e) {}
            throw new Error(msg);
        }
        const generateData = await generateRes.json();
        
        setStepState(4, 'completed');
        updateProgress(75);
        
        // --- STEP 5: Generating Texture ---
        setStepState(5, 'active');
        updateProgress(80);
        await sleep(800);
        setStepState(5, 'completed');
        updateProgress(88);
        
        // --- STEP 6: Optimizing Mesh ---
        setStepState(6, 'active');
        updateProgress(92);
        await sleep(600);
        setStepState(6, 'completed');
        updateProgress(96);
        
        // --- STEP 7: Saving Model and finalizing ---
        setStepState(7, 'active');
        updateProgress(98);
        await sleep(500);
        setStepState(7, 'completed');
        updateProgress(100);
        
        // Clean form upload fields
        document.getElementById('file-input').value = '';
        document.getElementById('asset-name-input').value = '';
        const slotsGrid = document.getElementById('image-slots-grid');
        if (slotsGrid) slotsGrid.style.display = 'none';
        const dragArea = document.getElementById('drag-drop-area');
        if (dragArea) dragArea.style.display = 'block';
        document.getElementById('btn-submit-generate').disabled = true;
        
        // Save generated asset details to view results
        AppState.activeAssetId = assetId;
        AppState.activeAssetData = generateData;
        
        // Small delay to admire completion before transferring to results
        setTimeout(() => {
            switchView('result');
        }, 800);
        
    } catch (error) {
        console.error("[AI Processing Failed]", error);
        alert(`Quá trình AI gặp lỗi: ${error.message}\n\nHệ thống sẽ quay lại màn hình tải lên.`);
        switchView('upload');
    }
}

function setStepState(stepNumber, state) {
    const card = document.getElementById(`step-${stepNumber}`);
    const statusBox = document.getElementById(`step-status-${stepNumber}`);
    
    if (!card || !statusBox) return;
    
    card.className = `step-card ${state}`;
    
    if (state === 'active') {
        statusBox.innerHTML = '<div class="step-loader"></div>';
    } else if (state === 'completed') {
        statusBox.innerHTML = '<span class="step-check"><i class="fa-solid fa-circle-check"></i></span>';
    } else {
        statusBox.innerHTML = '<span class="step-wait"><i class="fa-regular fa-clock"></i></span>';
    }
}

function updateProgress(percentage) {
    const bar = document.getElementById('processing-bar');
    const percentageText = document.getElementById('processing-percentage');
    if (bar) bar.style.width = `${percentage}%`;
    if (percentageText) percentageText.textContent = `Tiến độ: ${percentage}%`;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// ==========================================
// 5. INTERACTIVE RESULTS 3D VIEWER (THREE.JS)
// ==========================================
// Per-method orientation config (applied to modelRoot after load)
const METHOD_ORIENT = {
    'local_triposr_gpu': {
        // TripoSR exports Z-up; GLTF standard is Y-up.
        // The export pipeline applies rotation_matrix(-pi/2, X).
        // If still lying sideways, apply correction here.
        rotateX: 0,   // degrees; override if needed
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

function initResultViewer() {
    const container = document.getElementById('result-canvas-container');
    const loader = document.getElementById('viewer-loader');
    const errorEl = document.getElementById('viewer-error');
    if (!container || !AppState.activeAssetData) return;

    if (loader) loader.classList.add('active');
    if (errorEl) errorEl.style.display = 'none';
    container.innerHTML = '';

    // Safety: hide spinner after 15s if GLB hasn't loaded or errored
    if (loader) {
        setTimeout(function () {
            if (loader.classList.contains('active')) {
                loader.classList.remove('active');
                if (errorEl) {
                    errorEl.style.display = 'flex';
                    var detailEl = document.getElementById('viewer-error-detail');
                    if (detailEl) detailEl.textContent = 'Het thoi gian cho tai model. Vui long thu lai.';
                }
                console.warn('[ResultViewer] Spinner timeout after 15s');
            }
        }, 15000);
    }

    if (AppState.resultScene.animationId) {
        cancelAnimationFrame(AppState.resultScene.animationId);
    }

    const data = AppState.activeAssetData;
    const assetName = data.name || (data.asset && data.asset.name);
    const metrics = data.metrics || (data.asset && data.asset);
    const models = data.models || (data.asset && {
        glb: data.asset.model_glb,
        obj: data.asset.model_obj,
        ply: data.asset.model_ply
    });
    const originalImage = data.original_image || (data.asset && data.asset.original_image);
    const noBgImage = data.no_bg_image || (data.asset && data.asset.no_bg_image);
    const method = data.method || 'unknown';
    const assetId = data.asset_id || (data.asset && data.asset.id);

    // Images and metadata are now populated by _populateDrawerInput() into the left drawer.
    // Original elements (res-original-img, meta-name, etc.) no longer exist in the workspace HTML.
    // These assignments are skipped — drawer content is injected after GLB loads.

    // ── Scene ──
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0b12);
    scene.fog = new THREE.FogExp2(0x0a0b12, 0.06);
    AppState.resultScene.scene = scene;

    // ── Camera ──
    const camera = new THREE.PerspectiveCamera(35, container.clientWidth / container.clientHeight, 0.01, 100);
    camera.position.set(0, 0.8, 2.8);
    AppState.resultScene.camera = camera;

    // ── Renderer ──
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: false });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    renderer.outputEncoding = THREE.sRGBEncoding;
    container.appendChild(renderer.domElement);
    AppState.resultScene.renderer = renderer;

    // ── Studio Lighting ──
    const ambientLight = new THREE.AmbientLight(0x404060, 0.35);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0x87ceeb, 0x362d59, 0.5);
    hemiLight.position.set(0, 10, 0);
    scene.add(hemiLight);

    // Key light: warm from upper-right
    const keyLight = new THREE.DirectionalLight(0xffeedd, 2.0);
    keyLight.position.set(3.5, 5.5, 4.5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 20;
    keyLight.shadow.camera.left = -3;
    keyLight.shadow.camera.right = 3;
    keyLight.shadow.camera.top = 3;
    keyLight.shadow.camera.bottom = -3;
    keyLight.shadow.bias = -0.0005;
    scene.add(keyLight);

    // Fill light: cool from left
    const fillLight = new THREE.DirectionalLight(0x7799dd, 0.7);
    fillLight.position.set(-4.5, 2.5, -1.5);
    scene.add(fillLight);

    // Rim light: back edge highlight
    const rimLight = new THREE.DirectionalLight(0xbbccff, 0.9);
    rimLight.position.set(0, 3.5, -6);
    scene.add(rimLight);

    // Ground plane
    const groundGeo = new THREE.PlaneGeometry(10, 10);
    const groundMat = new THREE.MeshStandardMaterial({
        color: 0x0d0f1a,
        roughness: 0.95,
        metalness: 0.05,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.5;
    ground.receiveShadow = true;
    scene.add(ground);

    // Grid helper (togglable)
    const gridHelper = new THREE.GridHelper(6, 24, 0x1a2a60, 0x111a33);
    gridHelper.position.y = -0.49;
    gridHelper.material.transparent = true;
    gridHelper.material.opacity = 0.25;
    scene.add(gridHelper);
    AppState.resultScene.gridHelper = gridHelper;

    // ── Orbit Controls ──
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 + 0.05;
    controls.minDistance = 0.5;
    controls.maxDistance = 10;
    controls.target.set(0, 0, 0);
    AppState.resultScene.controls = controls;

    // ── Transform Controls (Gizmo) ──
    const transformControls = new THREE.TransformControls(camera, renderer.domElement);
    transformControls.setMode('translate');
    transformControls.setSpace('world');
    transformControls.setSize(0.8);
    scene.add(transformControls);
    AppState.resultScene.transformControls = transformControls;

    // Disable orbit while dragging gizmo
    let _gizmoDragging = false;
    transformControls.addEventListener('dragging-changed', function (event) {
        controls.enabled = !event.value;
        _gizmoDragging = event.value;
        if (!event.value && AppState.editor) {
            AppState.editor._saveSnapshot();
            AppState.editor._updateHistoryInfo();
        }
    });

    // Expose gizmo mode setter
    AppState.resultScene._setGizmoMode = function (mode) {
        if (mode === 'disable' || !mode) {
            transformControls.detach();
            return;
        }
        var mdl = AppState.resultScene.model;
        if (!mdl) return;
        transformControls.setMode(mode);
        if (transformControls.object !== mdl) {
            transformControls.attach(mdl);
        }
    };

    // ── Load GLB ──
    const gltfLoader = new THREE.GLTFLoader();
    console.log('[ResultViewer] Loading GLB:', models.glb);
    gltfLoader.load(
        models.glb,
        (gltf) => {
            console.log('[ResultViewer] GLB loaded successfully:', models.glb);
            // 1. modelRoot group — never add gltf.scene directly
            const modelRoot = new THREE.Group();
            modelRoot.add(gltf.scene);

            // 2. Center using Box3
            const box = new THREE.Box3().setFromObject(modelRoot);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);

            // Translate so center is at origin
            const offset = new THREE.Vector3().copy(center).negate();
            modelRoot.position.copy(offset);

            // 3. Scale to fit
            const targetSize = 1.8;
            const scale = targetSize / maxDim;
            modelRoot.scale.set(scale, scale, scale);

            // 4. Apply method-specific orientation as default
            const orientCfg = METHOD_ORIENT[method] || METHOD_ORIENT['template_retrieval'];
            modelRoot.rotation.set(
                orientCfg.rotateX * Math.PI / 180,
                orientCfg.rotateY * Math.PI / 180,
                orientCfg.rotateZ * Math.PI / 180
            );

            // 5. Recompute box after rotation, translate up so bottom sits at y=0
            modelRoot.updateMatrixWorld(true);
            const box2 = new THREE.Box3().setFromObject(modelRoot);
            const minY = box2.min.y;
            if (minY < 0) {
                modelRoot.position.y += -minY;
            }

            // 6. Enable shadows on meshes
            gltf.scene.traverse((child) => {
                if (child.isMesh) {
                    child.castShadow = true;
                    child.receiveShadow = true;
                    if (child.material) {
                        child.material.side = THREE.DoubleSide;
                        child.material.needsUpdate = true;
                    }
                }
            });

            scene.add(modelRoot);
            AppState.resultScene.model = modelRoot;
            AppState.resultScene.gltfScene = gltf.scene;
            AppState.resultScene.currentMethod = method;

            // 7. Fit camera to bounding sphere
            const sphere = new THREE.Sphere();
            new THREE.Box3().setFromObject(modelRoot).getBoundingSphere(sphere);
            const dist = sphere.radius * 2.8;
            const phi = 0.6;
            const theta = 0.4;
            camera.position.set(
                dist * Math.sin(theta) * Math.cos(phi),
                dist * 0.6 + sphere.center.y,
                dist * Math.cos(theta) * Math.cos(phi) + sphere.center.z
            );
            controls.target.copy(sphere.center);
            controls.update();

            // 8. Restore saved viewer orientation if exists
            _restoreOrientation(assetId, modelRoot, method);

            // 9. Initialize Asset Editor
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

            if (loader) loader.classList.remove('active');

            // Set asset name in top bar
            var nameEl = document.getElementById('res-asset-name');
            if (nameEl) nameEl.textContent = assetName || 'Asset 3D';

            // Populate left drawer with input content
            _populateDrawerInput(originalImage, noBgImage, assetName, metrics, method, models);

            // Initialize workspace UI
            initWorkspace();
        },
        undefined,
        (error) => {
            console.error('[Result Viewer] GLB load failed:', models.glb, error);
            if (loader) loader.classList.remove('active');
            if (errorEl) {
                errorEl.style.display = 'flex';
                var detailEl = document.getElementById('viewer-error-detail');
                if (detailEl) {
                    detailEl.textContent = 'URL: ' + (models.glb || 'N/A') + ' | ' + (error.message || 'Loi khong xac dinh');
                }
            }
        }
    );

    // ── Animation Loop ──
    let autoRotateActive = false;
    AppState.resultScene.autoRotate = false;

    function animate() {
        AppState.resultScene.animationId = requestAnimationFrame(animate);

        if (autoRotateActive && AppState.resultScene.model) {
            AppState.resultScene.model.rotation.y += 0.008;
        }

        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    // Expose auto-rotate setter for toolbar
    AppState.resultScene._setAutoRotate = function(on) {
        autoRotateActive = on;
        AppState.resultScene.autoRotate = on;
    };
}

// ── Orientation persistence ──
function _saveOrientation(assetId) {
    if (!assetId) return;
    const root = AppState.resultScene.model;
    if (!root) return;
    const data = {
        rx: root.rotation.x,
        ry: root.rotation.y,
        rz: root.rotation.z,
        px: root.position.x,
        py: root.position.y,
        pz: root.position.z,
        sx: root.scale.x,
        sy: root.scale.y,
        sz: root.scale.z
    };
    try {
        localStorage.setItem('viewer_orient_' + assetId, JSON.stringify(data));
        const hint = document.getElementById('orient-hint');
        if (hint) hint.textContent = '✓ Đã lưu hướng (chỉ viewer)';
    } catch(e) {}
}

function _restoreOrientation(assetId, modelRoot, method) {
    if (!assetId || !modelRoot) return;
    try {
        const raw = localStorage.getItem('viewer_orient_' + assetId);
        if (raw) {
            const d = JSON.parse(raw);
            modelRoot.rotation.set(d.rx || 0, d.ry || 0, d.rz || 0);
            modelRoot.position.set(d.px || 0, d.py || 0, d.pz || 0);
            modelRoot.scale.set(d.sx || 1, d.sy || 1, d.sz || 1);
            const hint = document.getElementById('orient-hint');
            if (hint) hint.textContent = 'Đã khôi phục hướng đã lưu';
        }
    } catch(e) {}
}

// ── Camera presets ──
function _setCameraPreset(view) {
    const camera = AppState.resultScene.camera;
    const controls = AppState.resultScene.controls;
    const model = AppState.resultScene.model;
    if (!camera || !controls) return;

    let target = new THREE.Vector3(0, 0, 0);
    if (model) {
        new THREE.Box3().setFromObject(model).getCenter(target);
    }

    let dist = 2.5;
    if (model) {
        const sphere = new THREE.Sphere();
        new THREE.Box3().setFromObject(model).getBoundingSphere(sphere);
        dist = sphere.radius * 3;
    }

    const pos = new THREE.Vector3();
    switch (view) {
        case 'front':    pos.set(0, 0, dist); break;
        case 'left':     pos.set(-dist, 0, 0); break;
        case 'right':    pos.set(dist, 0, 0); break;
        case 'top':      pos.set(0, dist, 0.01); break;
        case 'perspective':
        default:
            pos.set(dist * 0.5, dist * 0.6, dist);
            break;
    }
    camera.position.copy(pos);
    controls.target.copy(target);
    controls.update();
}

function loadOBJFallback(objUrl, mtlUrl, scene, loader) {
    if (!objUrl) return;
    const mtlLoader = new THREE.MTLLoader();
    mtlLoader.load(mtlUrl, (materials) => {
        materials.preload();
        const objLoader = new THREE.OBJLoader();
        objLoader.setMaterials(materials);
        objLoader.load(objUrl, (obj) => {
            const box = new THREE.Box3().setFromObject(obj);
            const size = box.getSize(new THREE.Vector3());
            const center = box.getCenter(new THREE.Vector3());
            
            obj.position.x += (obj.position.x - center.x);
            obj.position.y += (obj.position.y - center.y);
            obj.position.z += (obj.position.z - center.z);
            
            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = 1.3 / maxDim;
            obj.scale.set(scale, scale, scale);
            
            scene.add(obj);
            AppState.resultScene.model = obj;
            if (loader) loader.classList.remove('active');
        }, null, (err) => {
            console.error('OBJ Loader failed too', err);
            if (loader) loader.classList.remove('active');
        });
    });
}

function initResultToolbar() {
    const btnRotate = document.getElementById('btn-tool-rotate');
    const btnPan = document.getElementById('btn-tool-pan');
    const btnReset = document.getElementById('btn-tool-reset');
    const btnFullscreen = document.getElementById('btn-tool-fullscreen');
    const btnGrid = document.getElementById('btn-tool-grid');
    const btnUseInClassroom = document.getElementById('btn-use-in-classroom');
    
    if (!btnRotate) return;
    
    // Auto Rotate toggle — only active when user clicks
    btnRotate.addEventListener('click', () => {
        const on = !btnRotate.classList.contains('active');
        btnRotate.classList.toggle('active', on);
        if (AppState.resultScene._setAutoRotate) {
            AppState.resultScene._setAutoRotate(on);
        }
    });
    
    // Pan Mode toggle
    btnPan.addEventListener('click', () => {
        const controls = AppState.resultScene.controls;
        if (controls) {
            btnPan.classList.toggle('active');
            if (btnPan.classList.contains('active')) {
                controls.mouseButtons = {
                    LEFT: THREE.MOUSE.PAN,
                    MIDDLE: THREE.MOUSE.DOLLY,
                    RIGHT: THREE.MOUSE.ROTATE
                };
            } else {
                controls.mouseButtons = {
                    LEFT: THREE.MOUSE.ROTATE,
                    MIDDLE: THREE.MOUSE.DOLLY,
                    RIGHT: THREE.MOUSE.PAN
                };
            }
        }
    });
    
    // Grid toggle
    if (btnGrid) {
        btnGrid.addEventListener('click', () => {
            const gh = AppState.resultScene.gridHelper;
            if (gh) {
                gh.visible = !gh.visible;
                btnGrid.classList.toggle('active', gh.visible);
            }
        });
        btnGrid.classList.add('active');
    }
    
    // Reset camera + model rotation to method default
    btnReset.addEventListener('click', () => {
        const camera = AppState.resultScene.camera;
        const controls = AppState.resultScene.controls;
        const model = AppState.resultScene.model;
        const method = AppState.resultScene.currentMethod;
        if (camera && controls && model) {
            const orientCfg = METHOD_ORIENT[method] || METHOD_ORIENT['template_retrieval'];
            model.rotation.set(
                orientCfg.rotateX * Math.PI / 180,
                orientCfg.rotateY * Math.PI / 180,
                orientCfg.rotateZ * Math.PI / 180
            );
            model.updateMatrixWorld(true);
            const box = new THREE.Box3().setFromObject(model);
            const minY = box.min.y;
            if (minY < 0) {
                model.position.y += -minY;
            } else if (minY > 0.01) {
                model.position.y -= minY;
            }
            _setCameraPreset('perspective');
            const hint = document.getElementById('orient-hint');
            if (hint) hint.textContent = '';
        }
    });
    
    // Fullscreen toggle
    btnFullscreen.addEventListener('click', () => {
        var viewportBox = document.querySelector('.ws-canvas');
        if (!viewportBox) return;
        if (!document.fullscreenElement) {
            viewportBox.requestFullscreen().catch(err => {
                alert(`Khong the kich hoat toan man hinh: ${err.message}`);
            });
            btnFullscreen.innerHTML = '<i class="fa-solid fa-minimize"></i>';
        } else {
            document.exitFullscreen();
            btnFullscreen.innerHTML = '<i class="fa-solid fa-maximize"></i>';
        }
    });
    
    document.addEventListener('fullscreenchange', () => {
        if (!document.fullscreenElement) {
            btnFullscreen.innerHTML = '<i class="fa-solid fa-maximize"></i>';
        }
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 150);
    });
    
    // ── Orientation Buttons ──
    document.querySelectorAll('.orient-btn[data-axis]').forEach(btn => {
        btn.addEventListener('click', () => {
            const model = AppState.resultScene.model;
            if (!model) return;
            const axis = btn.dataset.axis;
            const angle = parseFloat(btn.dataset.angle) * Math.PI / 180;
            if (axis === 'x') model.rotation.x += angle;
            else if (axis === 'y') model.rotation.y += angle;
            else if (axis === 'z') model.rotation.z += angle;
            model.updateMatrixWorld(true);
            const box = new THREE.Box3().setFromObject(model);
            const minY = box.min.y;
            if (minY < 0) {
                model.position.y += -minY;
            }
            const hint = document.getElementById('orient-hint');
            if (hint) hint.textContent = 'Đã xoay (chưa lưu)';
        });
    });
    
    // Set default upright
    const btnDefault = document.getElementById('btn-orient-default');
    if (btnDefault) {
        btnDefault.addEventListener('click', () => {
            const model = AppState.resultScene.model;
            const method = AppState.resultScene.currentMethod;
            if (!model) return;
            const orientCfg = METHOD_ORIENT[method] || METHOD_ORIENT['template_retrieval'];
            model.rotation.set(
                orientCfg.rotateX * Math.PI / 180,
                orientCfg.rotateY * Math.PI / 180,
                orientCfg.rotateZ * Math.PI / 180
            );
            model.updateMatrixWorld(true);
            const box = new THREE.Box3().setFromObject(model);
            const minY = box.min.y;
            if (minY < 0) {
                model.position.y += -minY;
            }
            const hint = document.getElementById('orient-hint');
            if (hint) hint.textContent = 'Đã đặt đứng mặc định';
        });
    }
    
    // Save orientation
    const btnSave = document.getElementById('btn-orient-save');
    if (btnSave) {
        btnSave.addEventListener('click', () => {
            const data = AppState.activeAssetData;
            const assetId = data.asset_id || (data.asset && data.asset.id);
            _saveOrientation(assetId);
        });
    }
    
    // ── Camera Presets ──
    document.querySelectorAll('.cam-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            _setCameraPreset(btn.dataset.view);
        });
    });
    
    // Transition current model to Classroom Sandbox
    if (btnUseInClassroom) {
        btnUseInClassroom.addEventListener('click', () => {
            if (AppState.activeAssetId) {
                switchView('classroom');
                setTimeout(() => {
                    loadModelInClassroom(AppState.activeAssetId);
                }, 300);
            }
        });
    }

    // ── Gizmo Toolbar ──
    document.querySelectorAll('.gizmo-btn[data-gizmo]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var mode = btn.dataset.gizmo;
            if (AppState.resultScene._setGizmoMode) {
                AppState.resultScene._setGizmoMode(mode);
            }
            document.querySelectorAll('.gizmo-btn[data-gizmo]').forEach(function (b) {
                b.classList.toggle('active', b.dataset.gizmo === mode);
            });
        });
    });

    // Gizmo: Floor
    var gizmoFloor = document.getElementById('gizmo-btn-floor');
    if (gizmoFloor) {
        gizmoFloor.addEventListener('click', function () {
            var model = AppState.resultScene.model;
            if (!model) return;
            if (AppState.editor) AppState.editor._saveSnapshot();
            model.updateMatrixWorld(true);
            var box = new THREE.Box3().setFromObject(model);
            var minY = box.min.y;
            model.position.y += (-0.5 - minY);
            model.updateMatrixWorld(true);
            var hint = document.getElementById('orient-hint');
            if (hint) hint.textContent = 'Đã đặt đáy';
        });
    }

    // Gizmo: Reset
    var gizmoReset = document.getElementById('gizmo-btn-reset');
    if (gizmoReset) {
        gizmoReset.addEventListener('click', function () {
            var model = AppState.resultScene.model;
            var method = AppState.resultScene.currentMethod;
            if (!model) return;
            if (AppState.editor) AppState.editor._saveSnapshot();
            var orientCfg = METHOD_ORIENT[method] || METHOD_ORIENT['template_retrieval'];
            model.rotation.set(
                orientCfg.rotateX * Math.PI / 180,
                orientCfg.rotateY * Math.PI / 180,
                orientCfg.rotateZ * Math.PI / 180
            );
            model.position.set(0, 0, 0);
            model.scale.set(1, 1, 1);
            model.updateMatrixWorld(true);
            var box = new THREE.Box3().setFromObject(model);
            var minY = box.min.y;
            if (minY < 0) model.position.y += -minY;
            var hint = document.getElementById('orient-hint');
            if (hint) hint.textContent = 'Đã reset';
        });
    }
}


// ==========================================
// 6. LIBRARY GRID POPULATION, SEARCH & DELETE
// ==========================================
async function loadLibrary() {
    const grid = document.getElementById('library-assets-grid');
    const emptyState = document.getElementById('library-empty-state');
    const searchInput = document.getElementById('library-search');
    const sortSelect = document.getElementById('library-sort');
    
    if (!grid) return;
    
    grid.innerHTML = '<div class="text-center w-100 p-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 text-muted">Đang tải thư viện assets...</p></div>';
    emptyState.classList.add('d-none');
    
    try {
        const query = searchInput.value.trim();
        const res = await fetch(`/api/assets?search=${encodeURIComponent(query)}`);
        const data = await res.json();
        
        if (!res.ok || !data.success) {
            throw new Error('Không thể tải thư viện.');
        }
        
        let assets = data.assets;
        
        // Custom Sorting
        const sortVal = sortSelect.value;
        if (sortVal === 'oldest') {
            assets.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        } else if (sortVal === 'name_asc') {
            assets.sort((a, b) => a.name.localeCompare(b.name));
        }
        
        grid.innerHTML = '';
        
        if (assets.length === 0) {
            emptyState.classList.remove('d-none');
            return;
        }
        
        assets.forEach(asset => {
            const card = document.createElement('div');
            card.className = 'asset-card';
            
            // Build card html content
            const noBgImg = asset.no_bg_image || asset.original_image;
            const dateObj = new Date(asset.created_at);
            const dateStr = `${dateObj.getDate().toString().padStart(2, '0')}/${(dateObj.getMonth() + 1).toString().padStart(2, '0')}/${dateObj.getFullYear()}`;
            
            card.innerHTML = `
                <div class="asset-thumb">
                    <img src="${noBgImg}" alt="${asset.name}">
                    <span class="asset-status">AI ACTIVE</span>
                </div>
                <div class="asset-info">
                    <div class="asset-title" title="${asset.name}">${asset.name}</div>
                    <div class="asset-date"><i class="fa-regular fa-calendar me-1"></i> Ngày tạo: ${dateStr}</div>
                    <div class="asset-actions">
                        <button class="btn btn-primary btn-glow btn-card" onclick="viewAssetDetails(${asset.id}, event)">
                            <i class="fa-solid fa-cube me-1"></i> Xem lại 3D
                        </button>
                        <button class="btn-delete" title="Xóa vĩnh viễn" onclick="deleteAsset(${asset.id}, event)">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
        
    } catch (err) {
        console.error(err);
        grid.innerHTML = `<div class="alert alert-danger m-3 w-100">Gặp sự cố khi kết nối cơ sở dữ liệu: ${err.message}</div>`;
    }
}

// Search and Sort Event Listeners
const searchInput = document.getElementById('library-search');
const sortSelect = document.getElementById('library-sort');
if (searchInput) {
    // Debounced search
    let timeout = null;
    searchInput.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(loadLibrary, 350);
    });
}
if (sortSelect) {
    sortSelect.addEventListener('change', loadLibrary);
}

// ==========================================
// 6b. TEMPLATE LIBRARY (Thư Viện Khuôn Mẫu)
// ==========================================
let _templatesCache = [];

async function loadTemplates() {
    const grid = document.getElementById('templates-grid');
    const emptyState = document.getElementById('templates-empty-state');
    const countEl = document.getElementById('templates-count');
    const searchInput = document.getElementById('templates-search');
    const sortSelect = document.getElementById('templates-sort');
    if (!grid) return;

    grid.innerHTML = '<div class="text-center w-100 p-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 text-muted">Đang tải thư viện khuôn mẫu...</p></div>';
    if (emptyState) emptyState.classList.add('d-none');

    try {
        const res = await fetch('/api/templates');
        const data = await res.json();
        if (!res.ok || !data.success) throw new Error('Không thể tải thư viện khuôn mẫu.');
        _templatesCache = data.templates;

        let templates = [..._templatesCache];
        const q = (searchInput ? searchInput.value : '').trim().toLowerCase();
        if (q) {
            templates = templates.filter(t =>
                (t.name || '').toLowerCase().includes(q) ||
                (t.category || '').toLowerCase().includes(q) ||
                (t.uid || '').toLowerCase().includes(q)
            );
        }
        if (sortSelect) {
            if (sortSelect.value === 'size_asc') templates.sort((a, b) => a.size_mb - b.size_mb);
            else if (sortSelect.value === 'size_desc') templates.sort((a, b) => b.size_mb - a.size_mb);
            else templates.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        }

        if (countEl) countEl.textContent = `Hiển thị ${templates.length} / ${_templatesCache.length} khuôn mẫu`;
        grid.innerHTML = '';

        if (templates.length === 0) {
            if (emptyState) emptyState.classList.remove('d-none');
            return;
        }

        templates.forEach((t, i) => {
            const card = document.createElement('div');
            card.className = 'asset-card';
            const thumbSrc = t.has_thumbnail
                ? `/api/templates/${t.uid}/thumbnail`
                : '/static/img/template_placeholder.png';
            const shortUid = t.uid.slice(0, 12);
            card.innerHTML = `
                <div class="asset-thumb">
                    <img src="${thumbSrc}" alt="${t.name}" loading="lazy" onerror="this.src='/static/img/template_placeholder.png'">
                    <span class="asset-status">KHUÔN MẪU</span>
                </div>
                <div class="asset-info">
                    <div class="asset-title" title="${t.uid}">${t.name}</div>
                    <div class="asset-date"><i class="fa-solid fa-database me-1"></i> ${t.size_mb} MB · ${shortUid}…</div>
                    <div class="asset-actions">
                        <button class="btn btn-primary btn-glow btn-card" onclick="importTemplate('${t.uid}', '${t.name.replace(/'/g, "\\'")}')">
                            <i class="fa-solid fa-download me-1"></i> Nhập vào Asset
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        console.error(err);
        grid.innerHTML = `<div class="alert alert-danger m-3 w-100">Gặp sự cố khi tải thư viện khuôn mẫu: ${err.message}</div>`;
    }
}

async function importTemplate(uid, name) {
    try {
        const res = await fetch(`/api/templates/${uid}/import`, { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(`✓ ${data.message}\nChuyển đến Thư Viện Asset để xem khuôn mẫu đã nhập.`);
            switchView('library');
            loadLibrary();
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể nhập khuôn mẫu.'));
        }
    } catch (e) {
        console.error(e);
        alert('Gặp lỗi khi nhập khuôn mẫu.');
    }
}

const tplSearchInput = document.getElementById('templates-search');
const tplSortSelect = document.getElementById('templates-sort');
if (tplSearchInput) {
    let tplTimeout = null;
    tplSearchInput.addEventListener('input', () => {
        clearTimeout(tplTimeout);
        tplTimeout = setTimeout(loadTemplates, 350);
    });
}
if (tplSortSelect) {
    tplSortSelect.addEventListener('change', loadTemplates);
}

async function viewAssetDetails(assetId, event) {
    if (event) event.stopPropagation();
    try {
        const res = await fetch(`/api/assets/${assetId}`);
        const data = await res.json();
        if (res.ok && data.success) {
            AppState.activeAssetId = assetId;
            AppState.activeAssetData = {
                success: true,
                name: data.asset.name,
                metrics: data.asset,
                models: {
                    glb: data.asset.model_glb,
                    obj: data.asset.model_obj,
                    ply: data.asset.model_ply
                },
                original_image: data.asset.original_image,
                no_bg_image: data.asset.no_bg_image
            };
            switchView('result');
        } else {
            alert('Không tìm thấy tài nguyên 3D.');
        }
    } catch (e) {
        console.error(e);
        alert('Gặp lỗi khi truy xuất thông tin asset.');
    }
}

async function deleteAsset(assetId, event) {
    if (event) event.stopPropagation();
    
    if (!confirm('Bạn có chắc chắn muốn xóa vĩnh viễn mô hình 3D này cùng toàn bộ các tệp OBJ, GLB liên quan? Thao tác này không thể hoàn tác.')) {
        return;
    }
    
    try {
        const res = await fetch(`/api/assets/${assetId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (res.ok && data.success) {
            loadLibrary();
        } else {
            alert(data.error || 'Lỗi không thể xóa.');
        }
    } catch (e) {
        console.error(e);
        alert('Gặp lỗi khi xóa tệp tài nguyên.');
    }
}


// ==========================================
// 7. EDUCATIONAL GAME SIMULATION (CLASSROOM VIEW)
// ==========================================
function initClassroomViewer() {
    const container = document.getElementById('classroom-canvas-container');
    const loader = document.getElementById('classroom-loader');
    
    if (!container || AppState.classroomScene.animationId) return;
    
    // Clear viewport
    container.innerHTML = '';
    if (loader) loader.classList.add('active');
    
    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x11131e);
    AppState.classroomScene.scene = scene;
    
    // Camera
    const camera = new THREE.PerspectiveCamera(40, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.set(0, 2.0, 4.5);
    AppState.classroomScene.camera = camera;
    
    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    renderer.outputEncoding = THREE.sRGBEncoding;
    container.appendChild(renderer.domElement);
    AppState.classroomScene.renderer = renderer;
    
    // Orbit Controls
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02; // Prevent going underneath floor
    controls.minDistance = 1.5;
    controls.maxDistance = 12;
    AppState.classroomScene.controls = controls;
    
    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.35);
    scene.add(ambientLight);
    
    // Soft overhead classroom ceiling panel light
    const ceilingLight = new THREE.DirectionalLight(0xffffff, 0.5);
    ceilingLight.position.set(0, 6, 0);
    scene.add(ceilingLight);
    
    // Spotlight focusing on the center desk
    const spotLight = new THREE.SpotLight(0x3b82f6, 3, 15, Math.PI / 4, 0.5, 1);
    spotLight.position.set(0, 4.5, 0);
    spotLight.castShadow = true;
    spotLight.shadow.mapSize.width = 1024;
    spotLight.shadow.mapSize.height = 1024;
    spotLight.shadow.bias = -0.0005;
    scene.add(spotLight);

    // Warm sun light casting clean shadow
    const sunLight = new THREE.DirectionalLight(0xfff8e7, 1.2);
    sunLight.position.set(4, 5, 3);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);
    
    // Create Virtual Teacher/Student wooden Desk
    const deskGroup = new THREE.Group();
    
    // Warm wood table top
    const topGeo = new THREE.BoxGeometry(2.4, 0.08, 1.4);
    const topMat = new THREE.MeshStandardMaterial({
        color: 0x8B5A2B, // Warm brown
        roughness: 0.6,
        metalness: 0.1
    });
    const tableTop = new THREE.Mesh(topGeo, topMat);
    tableTop.position.y = 0.6;
    tableTop.receiveShadow = true;
    tableTop.castShadow = true;
    deskGroup.add(tableTop);
    
    // Iron desk legs
    const legGeo = new THREE.CylinderGeometry(0.04, 0.03, 0.6);
    const legMat = new THREE.MeshStandardMaterial({ color: 0x222530, roughness: 0.5, metalness: 0.8 });
    
    const legOffsets = [
        [-1.0, 0.3, -0.5],
        [1.0, 0.3, -0.5],
        [-1.0, 0.3, 0.5],
        [1.0, 0.3, 0.5]
    ];
    
    legOffsets.forEach(pos => {
        const leg = new THREE.Mesh(legGeo, legMat);
        leg.position.set(pos[0], pos[1], pos[2]);
        leg.castShadow = true;
        deskGroup.add(leg);
    });
    
    scene.add(deskGroup);
    AppState.classroomScene.deskModel = deskGroup;
    
    // Ground Grid / Floor mimicking classroom floor
    const floorGeo = new THREE.PlaneGeometry(15, 15);
    const floorMat = new THREE.MeshStandardMaterial({
        color: 0x141622,
        roughness: 0.9,
        metalness: 0.05
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = 0;
    floor.receiveShadow = true;
    scene.add(floor);
    
    const floorGrid = new THREE.GridHelper(15, 20, 0x3b82f6, 0x1d2130);
    floorGrid.position.y = 0.005;
    scene.add(floorGrid);
    
    // Classroom blackboard backdrop panel representation
    const boardGeo = new THREE.PlaneGeometry(5, 2.5);
    const boardMat = new THREE.MeshStandardMaterial({
        color: 0x142b24, // Chalkboard dark green
        roughness: 0.8
    });
    const blackboard = new THREE.Mesh(boardGeo, boardMat);
    blackboard.position.set(0, 2.0, -3.5);
    scene.add(blackboard);
    
    // Chalkboard wooden frame
    const frameGeo = new THREE.BoxGeometry(5.2, 2.7, 0.05);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x5c4033 });
    const boardFrame = new THREE.Mesh(frameGeo, frameMat);
    boardFrame.position.set(0, 2.0, -3.55);
    scene.add(boardFrame);
    
    // Focus camera onto desk top
    controls.target.set(0, 0.6, 0);
    controls.update();
    
    if (loader) loader.classList.remove('active');
    
    // Rendering Loop
    function animate() {
        if (AppState.currentView !== 'classroom') return;
        AppState.classroomScene.animationId = requestAnimationFrame(animate);
        
        controls.update();
        renderer.render(scene, camera);
    }
    
    animate();
}

async function loadClassroomAssets() {
    const listContainer = document.getElementById('classroom-assets-select-list');
    const emptyState = document.getElementById('classroom-empty-assets');
    
    if (!listContainer) return;
    
    listContainer.innerHTML = '<div class="text-center w-100 p-3"><div class="spinner-border spinner-border-sm text-info" role="status"></div></div>';
    emptyState.classList.add('d-none');
    
    try {
        const res = await fetch('/api/assets');
        const data = await res.json();
        
        if (res.ok && data.success) {
            const assets = data.assets;
            listContainer.innerHTML = '';
            
            if (assets.length === 0) {
                emptyState.classList.remove('d-none');
                return;
            }
            
            assets.forEach(asset => {
                const item = document.createElement('div');
                item.className = `select-item ${AppState.activeAssetId === asset.id ? 'selected' : ''}`;
                item.setAttribute('data-id', asset.id);
                
                item.innerHTML = `
                    <div class="select-thumb">
                        <img src="${asset.no_bg_image || asset.original_image}" alt="${asset.name}">
                    </div>
                    <div class="select-info">
                        <div class="select-name">${asset.name}</div>
                        <div class="select-meta">Dung lượng: ${asset.file_size}</div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    document.querySelectorAll('.select-item').forEach(i => i.classList.remove('selected'));
                    item.classList.add('selected');
                    loadModelInClassroom(asset.id);
                });
                
                listContainer.appendChild(item);
            });
            
            // Auto load active asset if selected previously
            if (AppState.activeAssetId) {
                const activeItem = listContainer.querySelector(`[data-id="${AppState.activeAssetId}"]`);
                if (activeItem) {
                    activeItem.classList.add('selected');
                    // Ensure it scrolls to view if long list
                    activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        }
    } catch (e) {
        console.error(e);
        listContainer.innerHTML = '<div class="text-danger p-2">Lỗi tải dữ liệu.</div>';
    }
}

async function loadModelInClassroom(assetId) {
    const scene = AppState.classroomScene.scene;
    const loader = document.getElementById('classroom-loader');
    
    if (!scene) return;
    
    // Show loading
    if (loader) loader.classList.add('active');
    
    // Clear any existing active asset model in the classroom sandbox
    if (AppState.classroomScene.activeAssetModel) {
        scene.remove(AppState.classroomScene.activeAssetModel);
        AppState.classroomScene.activeAssetModel = null;
    }
    
    // Fetch details
    try {
        const res = await fetch(`/api/assets/${assetId}`);
        const data = await res.json();
        
        if (!res.ok || !data.success) {
            throw new Error('Lỗi truy xuất tài nguyên 3D.');
        }
        
        const asset = data.asset;
        AppState.activeAssetId = asset.id;
        
        // Setup Control Gizmo labels
        document.getElementById('gizmo-object-name').textContent = `Tên: ${asset.name}`;
        
        // Reset slider UI controllers to default values
        document.getElementById('gizmo-pos-x').value = '0';
        document.getElementById('gizmo-pos-y').value = '0.64'; // Placed directly on top of desk (height is 0.6 + thickness is 0.04)
        document.getElementById('gizmo-rot-x').value = '0';
        document.getElementById('gizmo-rot-y').value = '0';
        document.getElementById('gizmo-scale').value = '1.0';
        
        // Load model
        const gltfLoader = new THREE.GLTFLoader();
        gltfLoader.load(
            asset.model_glb,
            (gltf) => {
                const model = gltf.scene;
                
                // Shadow support
                model.traverse(node => {
                    if (node.isMesh) {
                        node.castShadow = true;
                        node.receiveShadow = true;
                        if (node.material) {
                            node.material.side = THREE.DoubleSide;
                            node.material.shadowSide = THREE.DoubleSide;
                            node.material.needsUpdate = true;
                        }
                    }
                });
                
                // Adjust pivots and centering
                const box = new THREE.Box3().setFromObject(model);
                const size = box.getSize(new THREE.Vector3());
                const center = box.getCenter(new THREE.Vector3());
                
                model.position.x += (model.position.x - center.x);
                // Make its bottom rest at Y=0 relative to parent group pivots
                model.position.y += (model.position.y - box.min.y); 
                model.position.z += (model.position.z - center.z);
                
                // Normal scale fitting
                const maxDim = Math.max(size.x, size.y, size.z);
                const fitScale = 0.55 / maxDim; // Fit inside nice desk boundary bounds
                
                // Wrap in a parent pivot group to make translations extremely predictable
                const pivotGroup = new THREE.Group();
                pivotGroup.add(model);
                pivotGroup.scale.set(fitScale, fitScale, fitScale);
                
                // Set initial absolute positioning on the desk top
                pivotGroup.position.set(0, 0.64, 0); // X, Y, Z
                
                scene.add(pivotGroup);
                AppState.classroomScene.activeAssetModel = pivotGroup;
                
                // Display Gizmo side panel controls
                document.getElementById('classroom-gizmo-controls').style.display = 'block';
                if (loader) loader.classList.remove('active');
            },
            null,
            (err) => {
                console.error('[Classroom Viewer] GLTF load failed:', err);
                if (loader) loader.classList.remove('active');
                alert('Không thể tải mô hình GLB trong phòng học ảo.');
            }
        );
        
    } catch (e) {
        console.error(e);
        if (loader) loader.classList.remove('active');
    }
}

function initClassroomControls() {
    const pX = document.getElementById('gizmo-pos-x');
    const pY = document.getElementById('gizmo-pos-y');
    const rX = document.getElementById('gizmo-rot-x');
    const rY = document.getElementById('gizmo-rot-y');
    const sc = document.getElementById('gizmo-scale');
    const btnRemove = document.getElementById('btn-classroom-remove-model');
    const btnReset = document.getElementById('btn-classroom-reset-gizmos');
    
    if (!pX) return;
    
    // Bind position and rotation slider handlers to the selected mesh
    const updateMeshTransform = () => {
        const group = AppState.classroomScene.activeAssetModel;
        if (group) {
            group.position.x = parseFloat(pX.value);
            group.position.y = parseFloat(pY.value);
            
            // Rotate the nested child mesh inside group to keep clean pivot positions
            const childMesh = group.children[0];
            if (childMesh) {
                childMesh.rotation.x = parseFloat(rX.value);
                childMesh.rotation.y = parseFloat(rY.value);
            }
            
            const baseScale = group.userData.baseScale || 1.0;
            const sliderScale = parseFloat(sc.value);
            group.scale.set(sliderScale, sliderScale, sliderScale);
        }
    };
    
    pX.addEventListener('input', updateMeshTransform);
    pY.addEventListener('input', updateMeshTransform);
    rX.addEventListener('input', updateMeshTransform);
    rY.addEventListener('input', updateMeshTransform);
    sc.addEventListener('input', updateMeshTransform);
    
    // Clear/unmount asset from sandbox desk
    btnRemove.addEventListener('click', () => {
        const scene = AppState.classroomScene.scene;
        if (scene && AppState.classroomScene.activeAssetModel) {
            scene.remove(AppState.classroomScene.activeAssetModel);
            AppState.classroomScene.activeAssetModel = null;
            document.getElementById('classroom-gizmo-controls').style.display = 'none';
            document.querySelectorAll('.select-item').forEach(i => i.classList.remove('selected'));
            AppState.activeAssetId = null;
        }
    });
    
    // Reset transforms to default coordinates on desk
    btnReset.addEventListener('click', () => {
        pX.value = '0';
        pY.value = '0.64';
        rX.value = '0';
        rY.value = '0';
        sc.value = '1.0';
        updateMeshTransform();
    });
}


// ==========================================
// 8. 3D ASSET WORKSPACE UI
// ==========================================
var _wsInitialized = false;

function initWorkspace() {
    if (_wsInitialized) return;
    _wsInitialized = true;

    // Left rail buttons → open/close drawer
    var railBtns = document.querySelectorAll('.ws-rail-btn[data-panel]');
    railBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var panel = btn.dataset.panel;
            var drawer = document.getElementById('ws-drawer-left');
            var isActive = btn.classList.contains('active');

            // Close all rail active states
            railBtns.forEach(function (b) { b.classList.remove('active'); });

            if (isActive && drawer.classList.contains('open')) {
                // Toggle off: close drawer
                closeLeftDrawer();
            } else {
                // Open drawer with this panel content
                btn.classList.add('active');
                openLeftDrawer(panel);
            }
        });
    });

    // Drawer close button
    var closeBtn = document.getElementById('ws-drawer-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', function () {
            closeLeftDrawer();
        });
    }

    // Right panel toggle
    var panelToggle = document.getElementById('ws-panel-toggle');
    if (panelToggle) {
        panelToggle.addEventListener('click', function () {
            toggleRightPanel();
        });
    }

    // Top bar buttons
    var btnSave = document.getElementById('ws-btn-save');
    if (btnSave) {
        btnSave.addEventListener('click', function () {
            if (AppState.editor) AppState.editor.saveEditorState();
        });
    }
    var btnExport = document.getElementById('ws-btn-export');
    if (btnExport) {
        btnExport.addEventListener('click', function () {
            if (AppState.editor) AppState.editor.exportGLB();
        });
    }

    // Retry button
    var retryBtn = document.getElementById('btn-retry-load');
    if (retryBtn) {
        retryBtn.addEventListener('click', function () {
            initResultViewer();
        });
    }

    // Open input drawer by default
    openLeftDrawer('input');
}

function openLeftDrawer(panel) {
    var drawer = document.getElementById('ws-drawer-left');
    var title = document.getElementById('ws-drawer-title');
    var content = document.getElementById('ws-drawer-content');
    if (!drawer || !content) return;

    // Update title
    var titles = { input: 'Anh dau vao', info: 'Thong tin mo hinh', downloads: 'Tai xuong' };
    if (title) title.textContent = titles[panel] || panel;

    // Content is pre-populated, just show the right section
    var sections = content.querySelectorAll('.drawer-section');
    sections.forEach(function (s) {
        s.style.display = s.dataset.section === panel ? 'block' : 'none';
    });

    drawer.classList.add('open');
}

function closeLeftDrawer() {
    var drawer = document.getElementById('ws-drawer-left');
    if (drawer) drawer.classList.remove('open');
    document.querySelectorAll('.ws-rail-btn').forEach(function (b) { b.classList.remove('active'); });
}

function toggleRightPanel() {
    var panel = document.getElementById('ws-panel-right');
    var toggle = document.getElementById('ws-panel-toggle');
    var icon = toggle ? toggle.querySelector('i') : null;
    if (!panel) return;

    var w = window.innerWidth;
    if (w >= 1200) {
        // Desktop: collapse/expand
        panel.classList.toggle('collapsed');
        if (icon) {
            icon.className = panel.classList.contains('collapsed')
                ? 'fa-solid fa-chevron-left'
                : 'fa-solid fa-chevron-right';
        }
    } else if (w >= 768) {
        // Tablet: toggle drawer
        panel.classList.toggle('open');
    } else {
        // Mobile: toggle bottom sheet
        panel.classList.toggle('open');
    }
}

function _populateDrawerInput(originalImage, noBgImage, assetName, metrics, method, models) {
    var content = document.getElementById('ws-drawer-content');
    if (!content) return;

    var methodLabels = {
        'local_triposr_gpu': 'Local TripoSR (GPU CUDA)',
        'template_retrieval': 'CLIP Template Retrieval'
    };

    content.innerHTML = '' +
        '<div class="drawer-section" data-section="input">' +
            '<div class="drawer-img-box">' +
                '<h5>Anh goc</h5>' +
                '<img src="' + (originalImage || '') + '" alt="Original">' +
            '</div>' +
            '<div class="drawer-img-box transparent-bg">' +
                '<h5>Anh da cat nen</h5>' +
                '<img src="' + (noBgImage || originalImage || '') + '" alt="No BG">' +
            '</div>' +
        '</div>' +
        '<div class="drawer-section" data-section="info" style="display:none;">' +
            '<div class="drawer-meta-grid">' +
                '<div class="drawer-meta-item"><div class="metric-label">Ten vat the</div><div class="metric-value">' + (assetName || '-') + '</div></div>' +
                '<div class="drawer-meta-item accent-metric"><div class="metric-label">Phuong phap</div><div class="metric-value">' + (methodLabels[method] || method || '-') + '</div></div>' +
                '<div class="drawer-meta-item accent-metric"><div class="metric-label">Thoi gian</div><div class="metric-value">' + (metrics.inference_time || '0') + 's</div></div>' +
                '<div class="drawer-meta-item"><div class="metric-label">Dinh</div><div class="metric-value">' + Number(metrics.vertices || 0).toLocaleString() + '</div></div>' +
                '<div class="drawer-meta-item"><div class="metric-label">Mat</div><div class="metric-value">' + Number(metrics.faces || 0).toLocaleString() + '</div></div>' +
                '<div class="drawer-meta-item"><div class="metric-label">Texture</div><div class="metric-value">' + (metrics.texture_size || '1024x1024') + '</div></div>' +
                '<div class="drawer-meta-item"><div class="metric-label">Kich thuoc</div><div class="metric-value">' + (metrics.file_size || '0 MB') + '</div></div>' +
            '</div>' +
        '</div>' +
        '<div class="drawer-section" data-section="downloads" style="display:none;">' +
            '<div class="drawer-downloads">' +
                '<h5>Tai xuong dinh dang 3D:</h5>' +
                '<div class="drawer-download-btns">' +
                    '<a href="' + (models.glb || '#') + '" download><i class="fa-solid fa-cube"></i> GLB</a>' +
                    '<a href="' + (models.obj || '#') + '" download><i class="fa-solid fa-shapes"></i> OBJ</a>' +
                    '<a href="' + (models.ply || '#') + '" download><i class="fa-solid fa-layer-group"></i> PLY</a>' +
                '</div>' +
            '</div>' +
        '</div>';
}
