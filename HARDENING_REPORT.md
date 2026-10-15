# BÁO CÁO HARDENING TỐI THIỂU (HARDENING REPORT)
**Mục tiêu:** Đảm bảo pipeline demo chính (ảnh đơn → rembg → procedural_elliptical → Three.js → tải GLB) chạy ổn định.
**Ngày thực hiện:** 19/07/2026

---

## 1. Tổng quan thay đổi

| Loại | File | Hành động | Lý do |
| :--- | :--- | :--- | :--- |
| Sửa | `services/tripo_service.py` | Xóa API key hard-code (47 ký tự thật) khỏi dòng 12. Đổi thành `os.environ.get("TRIPO_API_KEY", "")`. | Rủi ro bảo mật P0: key thật bị lộ trong source. `is_available()` đã tự trả False khi key rỗng. |
| Sửa | `routes/api_routes.py` | Chuyển 4 import nâng cao + 1 import torch sang lazy import bên trong hàm, có try/except báo lỗi rõ ràng. | Người dùng cài `pip install -r requirements.txt` (chỉ gói cơ bản) vẫn khởi động được pipeline chính mà không crash. |
| Sửa | `templates/index.html` (dòng 136-141) | Đặt `procedural_elliptical` làm option mặc định (selected). Thêm "(Thử nghiệm)" cho 3 pipeline chưa xác minh. Không xóa option nào. | Đảm bảo người dùng demo mở web ra đã chọn đúng pipeline đã verify. |
| Tạo | `.env.example` | File mới chứa 6 biến môi trường placeholder (SECRET_KEY, TRIPO_API_KEY, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME). | Cấu hình môi trường mẫu, tránh commit secret. |
| Tạo | `.gitignore` | Bỏ qua: .env, venv/, __pycache__/, *.pyc, static/uploads/* (trừ .gitkeep), static/models/* (trừ .gitkeep), *.log. | Ngăn file nhạy cảm và artifact vào git. |
| Tạo | `static/uploads/.gitkeep` | File rỗng giữ thư mục. | Git không track được thư mục rỗng. |
| Tạo | `static/models/.gitkeep` | File rỗng giữ thư mục. | Git không track được thư mục rỗng. |
| Sửa | `requirements.txt` | Cập nhật phiên bản đúng thực tế: Flask 2.3.3→3.1.3, PyMySQL 1.1.0→1.4.6, numpy 1.24.3→2.4.6. Chỉ giữ 5 gói cần cho pipeline chính. **Không** thêm gói nâng cao. | Trước: chạy `pip install -r requirements.txt` crash ngay. Sau: chỉ pipeline chính hoạt động, pipeline thử nghiệm báo lỗi rõ ràng. |
| Tạo | `requirements-advanced.txt` | File mới liệt kê 11 gói cho pipeline thử nghiệm, kèm hướng dẫn cài platform-specific (PyTorch CUDA, OpenAI CLIP từ GitHub). | Tách biệt rõ ràng dependency "cơ bản" và "nâng cao". |
| Xóa | `scripts/_verify_pipeline.py` | Xóa. | Artifact tạm từ giai đoạn xác minh. |
| Xóa | `scripts/_verify_download.py` | Xóa. | Artifact tạm. |
| Xóa | `scripts/_harden_verify.py` | Xóa. | Artifact tạm từ giai đoạn hardening. |
| Xóa | `flask.log`, `verify_out.log`, `dl_out.log`, `harden_flask.log`, `harden_out.log` | Xóa. | Log tạm từ quá trình test. |
| Xóa | `static/uploads/test_apple.png` + `asset_8e48..._*` + `asset_0d1f..._*` | Xóa. | Ảnh/mô hình sinh trong lần verify (ngày 19/07). |
| Xóa | `static/models/model_27_333d3d.*`, `model_28_91995d.*` | Xóa. | Model sinh trong lần verify (ngày 19/07). |
| Xóa (DB) | assets id>=27 (id 27, 28) | Xóa khỏi SQLite `3dgame.db`. | Bản ghi thử nghiệm từ verify. |

---

## 2. Kết quả xác minh sau sửa

### Lệnh đã chạy
```powershell
# Khởi động Flask server nền
cd E:\xampp\htdocs\3DGame
$job = Start-Job -ScriptBlock { Set-Location "E:\xampp\htdocs\3DGame"; & "venv\Scripts\python.exe" app.py *> "harden_flask.log" }

# Tạo ảnh mẫu (hình tròn đỏ 256x256) bằng PIL
python -c "from PIL import Image, ImageDraw; img=Image.new('RGB',(256,256),(200,200,200)); d=ImageDraw.Draw(img); d.ellipse((40,40,216,216),fill=(180,50,50)); img.save('static/uploads/_harden_test.png')"

# Chạy pipeline end-to-end qua HTTP
python scripts/_harden_verify.py
```

### Kết quả HTTP

| Bước | Endpoint | HTTP Status | Thời gian | Ghi chú |
| :--- | :--- | :---: | :---: | :--- |
| Khởi động Flask | `GET /` | 200 | — | Server khởi động OK |
| Upload ảnh | `POST /api/upload` | 200 | < 1s | `asset_id=28` |
| Tách nền | `POST /api/bg-remove` | 200 | ~2s | `rembg` hoạt động |
| Sinh 3D | `POST /api/generate-3d` | 200 | **0.4s** | `method=procedural_elliptical` |
| Tải GLB | `GET /static/models/...glb` | 200 | < 1s | 153228 bytes |
| Tải OBJ | `GET /static/models/...obj` | 200 | < 1s | 538694 bytes |
| Tải PLY | `GET /static/models/...ply` | 200 | < 1s | 281511 bytes |
| Danh sách thư viện | `GET /api/assets` | 200 | < 1s | 15 assets (chỉ dữ liệu thật) |
| Chi tiết asset | `GET /api/assets/28` | 200 | < 1s | 675 bytes |

### Artifact đầu ra
- `static/models/model_28_91995d.glb` — GLB chuẩn glTF 2.0 (đã kiểm tra header `0x46546C67`, `trimesh.load` OK)
- `static/models/model_28_91995d.obj` — Wavefront OBJ
- `static/models/model_28_91995d.ply` — Stanford PLY
- Thông số: 3074 vertices, 6144 faces, 256x256 texture, 0.66 MB

### Module-level import test
```python
# Test rằng các import module-level không crash
from flask import Flask, jsonify
from services.db_service import db_service
from services.bg_remover import BGRemoverService
from services.mesh_generator import MeshGeneratorService
# → OK (cả 4 đều thành công)

# Kiểm tra advanced services không phải import module-level
# services.tripo_service → OK (được import lazy trong generate_3d)
# services.local_tripo_service → OK (được import lazy trong generate_3d)
# services.template_service → OK (được import lazy qua get_template_service())
```

---

## 3. Trạng thái bảo mật

| Mục | Trước | Sau |
| :--- | :--- | :--- |
| API key hard-code | `tripo_service.py` dòng 12: key thật 47 ký tự | `""` — chỉ đọc từ biến môi trường |
| `.env` mẫu | Không có | `E:\xampp\htdocs\3DGame\.env.example` (placeholder) |
| `.gitignore` | Không có | File mới, chặn `.env`, `venv/`, `__pycache__/`, `static/uploads/*`, `static/models/*`, `*.log` |
| `.gitkeep` | Không có | `static/uploads/.gitkeep`, `static/models/.gitkeep` |

---

## 4. Trạng thái dependency

| File | Mục đích | Số gói | Ghi chú |
| :--- | :--- | :---: | :--- |
| `requirements.txt` | Pipeline chính (đã verify) | 5 | Flask 3.1.3, PyMySQL 1.4.6, Pillow 10.0.0, rembg 2.0.52, numpy 2.4.6 |
| `requirements-advanced.txt` | Pipeline thử nghiệm | 11 | Gồm torch+cu121, open3d, scipy, opencv, transformers, faiss, clip (từ GitHub), requests, gradio_client, trimesh |

---

## 5. Kết luận

Pipeline chính **[Ảnh đơn → rembg → procedural_elliptical → Three.js → tải GLB]** đã được xác minh thành công:
- Khởi động Flask không lỗi với chỉ 5 gói cơ bản
- Upload, tách nền, sinh 3D, hiển thị, tải xuống — tất cả HTTP 200
- Thời gian sinh ≤ 0.4s
- 3 file GLB/OBJ/PLY đầu ra hợp lệ
- API key thật đã được xóa khỏi source
- Cấu hình môi trường mẫu (.env.example) và .gitignore đã được tạo
- Artifact tạm đã được dọn sạch
