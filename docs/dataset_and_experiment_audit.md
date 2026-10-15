# Dataset and Experiment Audit

## 1. Dataset Inventory

### GSO (Google Scanned Objects)
- **Trạng thái trong dự án**: ĐÃ TẢI MỘT PHẦN
- **Đường dẫn**: `static/templates/gso/` (~600+ object directories)
- **Mỗi object có**: `model.obj` (mesh GT), `renders/front.png` (ảnh render), textures
- **Cấu trúc**: Mỗi object một thư mục riêng với tên object_id
- **Đã chạy inference**: CÓ (10 objects pilot)
- **Log**: `experiments/logs/triposr_pilot.csv`, `triposr_pilot_metrics.json`
- **Prediction**: `experiments/outputs/predictions/triposr_pilot/` (10 subdirectories)
- **Manifest**: `experiments/data/manifests/gso_manifest.csv` (600+ objects)
- **Selected IDs**: `experiments/data/manifests/gso_selected_ids.csv`
- **Vai trò**: Đánh giá chính
- **Ground truth mesh**: Có (model.obj trong thư mục object)
- **Có thể tính CD/F-score**: CÓ, cần căn chỉnh hệ tọa độ

### ShapeNet / ShapeNetCore
- **Trạng thái trong dự án**: CHỈ KHẢO SÁT
- **Đường dẫn**: Không có thư mục dữ liệu thật
- **Có file manifest**: `experiments/data/manifests/dataset_manifest_shapenet.csv` (125 bytes)
- **Đã chạy inference**: CHƯA
- **Đã tải dữ liệu**: CHƯA
- **Vai trò**: Đối chiếu dự kiến, chưa thực nghiệm
- **TripoSR có được huấn luyện trên ShapeNet không?**: Có thể, cần xác nhận từ bài báo

### Pix3D
- **Trạng thái trong dự án**: CHỈ KHẢO SÁT
- **Đường dẫn**: Không có
- **Đã chạy inference**: CHƯA
- **Vai trò**: Tham khảo

### OmniObject3D
- **Trạng thái trong dự án**: CHỈ KHẢO SÁT
- **Đường dẫn**: Không có
- **Đã chạy inference**: CHƯA
- **Vai trò**: Tham khảo

### Objaverse / Objaverse-XL
- **Trạng thái trong dự án**: CHỈ KHẢO SÁT
- **Đường dẫn**: Không có (chỉ reference trong template catalog)
- **Đã chạy inference**: CHƯA
- **Vai trò**: Tham khảo pretraining context
- **TripoSR có được huấn luyện trên Objaverse không?**: Bài báo TripoSR gốc cho biết mô hình được huấn luyện trên tập dữ liệu tổng hợp từ nhiều nguồn bao gồm Objaverse, nhưng cần xác nhận phiên bản cụ thể.

## 2. Experiment Status

### Experiment: GSO Pilot (10 objects)
| Item | Status | Evidence |
|------|--------|----------|
| Ảnh input (render từ GSO) | CÓ | `static/templates/gso/*/renders/front.png` |
| Mesh ground truth | CÓ | `static/templates/gso/*/model.obj` |
| Prediction mesh | CÓ | `experiments/outputs/predictions/triposr_pilot/*/*.glb` |
| Log thời gian | CÓ | `experiments/logs/triposr_pilot.csv` |
| Log VRAM | CÓ | CSV column vram_before_mb, vram_peak_mb, vram_after_mb |
| Cold start log | CÓ | Sample 1 (52.3s) = cold start |
| Preview hình | CÓ | `experiments/outputs/predictions/triposr_pilot/*/preview.png` |
| Metrics JSON | CÓ | `triposr_pilot_metrics.json` |
| ShapeNet experiment | CHƯA | Không có dữ liệu ShapeNet |
| Rembg ablation | CHƯA | Chưa chạy |
| Multi-view experiment | CHƯA | Chưa chạy |
| Post-processing ablation | CHƯA | Chưa chạy |
| Geometry metrics (CD/F) | CHƯA | Cần protocol căn chỉnh |
| Qualitative rubric | CHƯA | Chưa chấm |

## 3. Claims to Fix in main.tex

| Claim | Issue | Fix |
|-------|-------|-----|
| "ShapeNet có hơn 3 triệu mô hình" | Không phân biệt ShapeNet tổng thể vs ShapeNetCore | Phân biệt rõ |
| "TripoSR được huấn luyện bằng Objaverse" | Chưa xác minh chính xác | Kiểm tra bài báo TripoSR |
| "Hậu xử lý bằng Poisson surface reconstruction" | Không tìm thấy trong code | Xóa |
| "Mesh phức tạp → thời gian lâu hơn" | Chưa kiểm tra tương quan | Ghi rõ chưa kết luận |
| "TripoSR điều chỉnh đỉnh theo độ phức tạp" | Chưa có evidence | Sửa hoặc xóa |
| "GLB 3,84 MB phù hợp mạng thông thường" | Chưa đo tốc độ mạng | Chuyển thành nhận xét dung lượng |
| "10 mẫu lấy từ GSO" | Đúng, nhưng là render không phải chụp thật | Làm rõ render từ GSO |
| "VRAM cần 807 MB" | Phép trừ VRAM hệ thống, không phải đo CUDA | Giữ nhưng ghi rõ cách đo |

## 4. Data Flow Verification

### Pipeline: Image → Mesh
```
GSO render front.png
    → [rembg] → nobg.png (KHÔNG có trong log, mặc định dùng render có nền trắng)
    → [TripoSR] → mesh.glb (trong predictions/triposr_pilot/*/)
    → [post-process] → final mesh
```

### Model locations
- TripoSR checkpoint: `tsr/system.py` references `model.ckpt` (pretrained)
- Model code: `tsr/` directory (copied from TripoSR source)
