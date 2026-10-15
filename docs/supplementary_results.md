# Supplementary Results

## Cold Start Analysis

| Statistic | Value | Notes |
|-----------|-------|-------|
| Mean (all 10) | 20.43 s | Includes cold start |
| Mean (warm, 9) | 16.89 s | Excluding first sample |
| Median | 17.35 s | Robust to outliers |
| Std Dev | 11.10 s | High due to cold start |
| Min | 11.8 s | Connect 4 Launchers |
| Max | 52.3 s | BAGEL_WITH_CHEESE (cold start) |

## VRAM

| Metric | Value |
|--------|-------|
| Peak VRAM | 2494 MB |
| Base VRAM | 1687 MB |
| Delta | 807 MB |
| GPU Total | 4 GB (RTX 2050) |
| Utilization | ~62% |

## Mesh Complexity

| Metric | Mean | Median | Min | Max |
|--------|------|--------|-----|-----|
| Vertices | 103,121 | 119,996 | 36,105 | 120,007 |
| Faces | 206,063 | 239,803 | 72,121 | 239,871 |
| GLB Size | 3.84 MB | 4.32 MB | 1.44 MB | 4.60 MB |

## Sample Details

| Sample | Time (s) | Vertices | Faces | GLB (MB) | VRAM (MB) |
|--------|----------|----------|-------|----------|-----------|
| BAGEL_WITH_CHEESE | 52.3 | 120002 | 239825 | 4.32 | 2494 |
| Dog | 18.2 | 120007 | 239783 | 4.32 | 2494 |
| Raccoon | 15.9 | 115001 | 229812 | 4.60 | 2494 |
| Razer BlackWidow Keyboard | 15.5 | 101529 | 202847 | 4.06 | 2494 |
| Hefty Waste Basket | 19.5 | 120001 | 239807 | 4.32 | 2494 |
| Connect 4 Launchers | 11.8 | 36105 | 72121 | 1.44 | 2494 |
| Timberland Shoe | 12.7 | 58571 | 117038 | 2.34 | 2494 |
| Cole Hardware School Bell | 17.1 | 120004 | 239799 | 4.32 | 2494 |
| Orchid Pot Ceramic Lime | 23.7 | 120004 | 239730 | 4.32 | 2494 |
| LEGO Star Wars Calendar | 17.6 | 119989 | 239871 | 4.32 | 2494 |

## Classification Branch (NOT IMPLEMENTED)

Các mô hình phân loại dự kiến:
- SVM (HOG features)
- Random Forest (HOG features)
- ResNet50 (pretrained, fine-tune)
- ViT-B/16 (pretrained, fine-tune)

Lý do chưa triển khai: thiếu dataset ảnh render có nhãn từ ShapeNet classes tương ứng với GSO samples.
