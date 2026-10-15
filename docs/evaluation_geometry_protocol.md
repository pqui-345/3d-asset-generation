# Geometry Evaluation Protocol

## Status: NOT IMPLEMENTED

Chưa có mesh ground truth được căn chỉnh cho các mẫu GSO trong pilot. Do đó chưa thể tính các metric hình học.

## Required Protocol (for future implementation)

### 1. Data Preparation
- Chọn N mẫu từ GSO có sẵn mesh ground truth (file .obj hoặc .glb từ bộ GSO gốc).
- Căn chỉnh prediction mesh và ground truth mesh về cùng hệ tọa độ (centroid, scale).
- Sử dụng ICP (Iterative Closest Point) để căn chỉnh cứng nếu cần.

### 2. Sampling
- Lấy mẫu đều trên bề mặt cả hai mesh: 10,000–100,000 points.
- Dùng Poisson disk sampling hoặc uniform mesh sampling.

### 3. Metrics
```
Chamfer Distance (CD):
  CD(P,Q) = (1/|P|) * sum_p min_q ||p-q||^2 + (1/|Q|) * sum_q min_p ||q-p||^2

F-score @ 1%:
  Precision = TP / (TP + FP)  where distance < threshold
  Recall    = TP / (TP + FN)
  F-score   = 2 * P * R / (P + R)

Normal Consistency (NC):
  NC = mean_p |n_p · n_q|  where q = NN(p)
```

### 4. Script
Script đề xuất: `evaluate_geometry.py` sử dụng `trimesh` và `numpy`.

```python
# evaluate_geometry.py (draft)
# python evaluate_geometry.py --pred <pred.glb> --gt <gt.obj> --samples 50000
# Returns: CD, F-score@1%, Precision, Recall, Normal Consistency
```

### 5. Requirements
- `trimesh` >= 3.12
- `numpy`
- `scipy` (for KDTree)

## Current Limitation
Need to:
1. Download ground truth meshes from GSO (original dataset)
2. Align coordinate systems (TripoSR outputs in normalized coordinates)
3. Implement and run evaluation
4. Log results to CSV
