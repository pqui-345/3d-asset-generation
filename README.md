# 3D Game — Hệ thống tự động tạo tài nguyên 3D từ ảnh chụp

## Giới thiệu
Hệ thống web demo cho phép người dùng tải lên ảnh chụp một vật thể và nhận lại mô hình 3D (GLB) có thể tương tác trên trình duyệt. Mô hình chính dùng TripoSR (pretrained) ở chế độ suy luận, kết hợp các pipeline phụ trợ (tách nền, truy vấn template, chuyển texture).

## Yêu cầu hệ thống
- Python 3.11
- NVIDIA GPU (CUDA 12.1), tối thiểu 4 GB VRAM
- 8 GB RAM
- Windows 10/11

## Cài đặt

### 1. Tạo môi trường ảo (khuyến nghị)
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Cài dependencies cơ bản
```bash
pip install -r requirements.txt
```

### 3. Cài dependencies nâng cao (GPU + pipeline thực nghiệm)
```bash
pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements-advanced.txt
```

### 4. Package `tsr` (TripoSR — package nội bộ, không có trên PyPI)
`tsr/` đã nằm sẵn trong dự án — chạy `app.py` từ thư mục gốc thì `import tsr` hoạt động bình thường, không cần cài thêm.

### 5. Tải trọng số mô hình TripoSR
File `services/weights/model.ckpt` (~1,6 GB) không được đóng gói trong mã nguồn do vượt giới hạn dung lượng. Tải về và đặt đúng vị trí:
```powershell
curl.exe -L -o services/weights/model.ckpt https://huggingface.co/stabilityai/TripoSR/resolve/main/model.ckpt
```
Vị trí chuẩn: `services/weights/config.yaml` + `services/weights/model.ckpt`

### 6. Tải dataset GSO (tùy chọn)
Dataset `static/templates/gso/` (~6 GB, 300 vật thể) không được đóng gói. Để chạy pipeline truy vấn template:
```bash
python scripts/download_gso.py
```

### 7. Cấu hình môi trường
```bash
copy .env.example .env
# Sửa SECRET_KEY và các tham số kết nối CSDL nếu cần
```

## Chạy hệ thống
```bash
python app.py
# Mở trình duyệt: http://localhost:5000
```

## Chạy thực nghiệm
```bash
# Pilot TripoSR trên 10 mẫu GSO
python experiments/scripts/run_triposr_pilot.py

# Thực nghiệm đầy đủ trên 30 mẫu GSO (kết quả lưu tại experiments/logs/ và experiments/outputs/)
python experiments/scripts/run_gso_experiment_30.py

# Đánh giá geometry (Chamfer, F1, Normal consistency...)
python experiments/scripts/run_geometry_metrics.py

# Tạo bảng/số liệu cho báo cáo
python experiments/scripts/make_tables_figures.py
```

## Cấu trúc thư mục
```
3DGame/
  app.py                    # Flask backend
  routes/                   # Route API và trang web
  services/                 # Backend services (TripoSR, tách nền, retrieval, texture...)
  tsr/                      # Package TripoSR (mô hình 3D từ ảnh)
  utils/ models/ scripts/   # Tiện ích, mô hình phụ trợ, script chuẩn bị dữ liệu
  templates/                # Frontend (index.html)
  static/css, js, img       # Tài nguyên giao diện
  data/                     # CSDL template (SQLite + FAISS index)
  3dgame.db                 # CSDL hệ thống
  experiments/              # Thực nghiệm: scripts, configs, logs, outputs, metrics
  requirements*.txt         # Dependencies
  .env.example              # Mẫu cấu hình
```

## Ghi chú bản quyền
- TripoSR: [MIT License](https://github.com/VAST-AI-Research/TripoSR), trọng số từ HuggingFace `stabilityai/TripoSR`.
- Dataset Google Scanned Objects (GSO): bản quyền riêng của Google (dùng cho mục đích nghiên cứu).
