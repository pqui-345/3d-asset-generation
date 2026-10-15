# Missing ShapeNet Experiment

## Current Status
**ShapeNetCore chưa được tải, chưa chạy inference.**

Trong dự án chỉ tồn tại file manifest:
- `experiments/data/manifests/dataset_manifest_shapenet.csv` (125 bytes)

Không có thư mục chứa mesh, ảnh render, hoặc kết quả inference cho ShapeNet.

## Required Protocol (future implementation)

### 1. Data Requirements
- **Phiên bản**: ShapeNetCore V1 hoặc V2
- **Dung lượng**: ~3.5 GB cho subset 13 classes
- **Các lớp gần giáo dục**: chair, table, airplane, car, vessel (5 classes)
- **Số mẫu đề xuất**: 3-5 mỗi lớp, tổng 15-25 mẫu

### 2. Expected Directory Structure
```
experiments/data/shapenet/ShapeNetCore.v2/
  ├── 02691156/  (airplane)
  │   ├── 1a04e3eab45ca15dd86060f189eb133/
  │   │   ├── models/model_normalized.obj
  │   │   └── ...
  │   └── ...
  ├── 02818832/  (bed)
  ├── 02958343/  (car)
  ├── 03001627/  (chair)
  └── 04379243/  (table)
```

### 3. Rendering Protocol
- Use Blender or pyrender for consistent rendering
- Fixed camera: azimuth 0°, elevation 30°, distance 2m
- Resolution: 512×512
- Background: white
- Lighting: 3-point studio setup
- Save metadata: camera pose, intrinsics, render timestamp

### 4. Inference Protocol
- Same TripoSR checkpoint as GSO pilot
- Single image per model (front view)
- Log time, VRAM, mesh stats

### 5. Geometry Evaluation
- Same protocol as GSO alignment
- Predict vs GT mesh after center/scale normalization
- Metrics: CD, Precision, Recall, F-score, Normal Consistency

### 6. Scripts Needed
- `scripts/render_shapenet.py` - render CAD models
- `scripts/inference_shapenet.py` - run TripoSR on renders
- Already have: `evaluate_geometry.py` (needs alignment refinement)

### 7. Impact on main.tex
- Section 4.6 "Kết quả ShapeNetCore" hiện ghi: "ShapeNetCore được khảo sát và thiết kế giao thức đối chiếu nhưng chưa được đưa vào kết quả định lượng do chưa có tập con và log thực nghiệm được xác minh."
