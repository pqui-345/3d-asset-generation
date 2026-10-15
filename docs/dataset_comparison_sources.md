# Dataset Comparison Sources

## Source Verification

### GSO (Google Scanned Objects)
- **Paper**: Downs et al., "Google Scanned Objects: A High-Quality Dataset of 3D Scanned Household Items", ICRA 2022
- **arXiv**: 2204.11918
- **Số lượng**: 1,000+ objects
- **Loại**: quét vật thể thật
- **License**: Creative Commons

### ShapeNet / ShapeNetCore
- **Paper**: Chang et al., "ShapeNet: An Information-Rich 3D Model Repository", arXiv 2015
- **arXiv**: 1512.03012
- **ShapeNet tổng thể**: 3,000,000+ models, 3,135 classes
- **ShapeNetCore V1**: 51,300 models, 55 classes (subset cleaned)
- **ShapeNetCore V2**: 52,472 models, 55 classes
- **Loại**: CAD tổng hợp

### Pix3D
- **Paper**: Sun et al., "Pix3D: Dataset and Methods for Single-Image 3D Shape Modeling", CVPR 2018
- **arXiv**: 1804.04610
- **Số lượng**: 9,469 ảnh, 395 models, 9 classes
- **Loại**: Ảnh chụp thật + CAD căn chỉnh
- **Đặc biệt**: Có cặp ảnh-mesh căn chỉnh pixel-level

### OmniObject3D
- **Paper**: Wu et al., "OmniObject3D: Large-Vocabulary 3D Object Dataset for Realistic Perception, Reconstruction and Generation", NeurIPS 2023
- **arXiv**: 2301.07525
- **Số lượng**: 6,000 objects, 190 classes
- **Loại**: quét vật thể thật

### Objaverse / Objaverse-XL
- **Ojaverse**: Deitke et al., "Objaverse: A Universe of Annotated 3D Objects", CVPR 2023
- **Objaverse-XL**: Deitke et al., "Objaverse-XL: A Universe of 10M+ 3D Objects", NeurIPS 2023
- **arXiv**: 2307.05663
- **Objaverse**: 800,000+ objects
- **Objaverse-XL**: 10,000,000+ objects
- **Loại**: tổng hợp từ nhiều nguồn (Sketchfab, thủ công, quét)

### TripoSR
- **Paper**: Tochilkin et al., "TripoSR: Fast 3D Object Reconstruction from a Single Image", arXiv 2024
- **arXiv**: 2403.02151
- **Training data**: According to paper, trained on a combination of Objaverse and other internal datasets
- **NOT trained on**: GSO, Pix3D, OmniObject3D specifically
- **Architecture**: Based on LRM (Large Reconstruction Model)

## Published Results on These Datasets

### ShapeNetCore (single-view reconstruction)
| Method | Year | CD (×10^-3) | F-score@1% | Notes |
|--------|------|------------|------------|-------|
| 3D-R2N2 | 2016 | - | - | Voxel output |
| Pixel2Mesh | 2018 | - | - | Mesh output |
| DISN | 2019 | - | - | Implicit surface |
| DMTet | 2021 | - | - | Hybrid |
| TripoSR | 2024 | Reported in paper | Reported | See paper for exact numbers |

*Note: Direct comparison requires identical test split, rendering protocol, sampling, and normalization.*

### GSO
- No standardized benchmark for single-view reconstruction exists
- Used primarily as source of photo-realistic 3D scans for simulation

### Pix3D
- Standardized benchmark: test split with aligned image-mesh pairs
- Metrics: CD, F-score, Normal Consistency
- TripoSR paper reports results on Pix3D

### OmniObject3D
- Has reconstruction benchmark but different protocol than ShapeNet

## Important Distinctions
- **ShapeNet** (tổng thể) vs **ShapeNetCore** (subset sạch)
- **Objaverse** (800K) vs **Objaverse-XL** (10M+)
- Training data của TripoSR KHÔNG phải toàn bộ Objaverse-XL
- Pix3D có ảnh thật, ShapeNet chỉ có render
