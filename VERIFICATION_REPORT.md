# BÁO CÁO XÁC MINH KỸ THUẬT (VERIFICATION REPORT)
**Giai đoạn:** Xác minh kỹ thuật (read-only + test tối thiểu an toàn)  
**Mục tiêu:** Phân biệt rõ "chức năng có code" với "chức năng chạy thật". Không thêm tính năng mới, không mở rộng phạm vi.  
**Ngày xác minh:** 19/07/2026

---

## A. Kiểm tra môi trường

### A.1 Phần mềm / phần cứng thực tế trên máy hiện tại
- **HĐH:** Windows (win32).
- **Python ( hệ thống `PATH`):** 3.11.9 (không có torch CUDA).
- **Python venv dự án (`venv\Scripts\python.exe`):** 3.11.9 ← đây là interpreter chính dùng để test.
- **pip:** 24.0.
- **GPU:** NVIDIA GeForce RTX 2050, VRAM 4 GB, Driver 581.86, CUDA Driver 13.0.
- **PyTorch (venv):** 2.5.1+cu121 → `torch.cuda.is_available() == True`.
- **MySQL (XAMPP):** KHÔNG chạy → `db_service` tự fallback sang SQLite (`3dgame.db`). Xác nhận bằng log: `[DB] Using SQLite database at: E:\xampp\htdocs\3DGame\3dgame.db`.

### A.2 Đối chiếu import thực tế trong source với `requirements.txt`

| Module import thật trong source | Có trong requirements.txt | Đã cài trong venv | Phiên bản venv | Phân loại | Ghi chú mâu thuẫn |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `flask` | Có (==2.3.3) | Có | 3.1.3 | **Bắt buộc web** | **Mâu thuẫn phiên bản** (yêu cầu 2.3.3, chạy 3.1.3). API Flask 3 khác 2.3 ở một số điểm (vd `__version__`). |
| `pymysql` | Có (==1.1.0) | Có | 1.4.6 | **Bắt buộc web** | Mâu thuẫn nhẹ, không phát sinh lỗi khi test. |
| `PIL` (Pillow) | Có (==10.0.0) | Có | 10.0.0 | **Bắt buộc web** | Khớp. |
| `rembg` | Có (==2.0.52) | Có | 2.0.52 | **Bắt buộc web** (pipeline tách nền chính) | Khớp. |
| `numpy` | Có (==1.24.3) | Có | **2.4.6** | **Bắt buộc web** | **Mâu thuẫn phiên bản nghiêm trọng**. NumPy 2.x breaking changes so với 1.24; một số API của rembg/transformers có thể lỗi với NumPy 2.x. |
| `torch` | KHÔNG | Có | 2.5.1+cu121 | **AI chính** | Thiếu trong requirements.txt. |
| `trimesh` | KHÔNG | Có | 4.12.2 | **AI chính** | Thiếu trong requirements.txt. |
| `open3d` | KHÔNG | Có | 0.19.0 | **AI chính** (Local TripoSR Poisson) | Thiếu trong requirements.txt. |
| `scipy` | KHÔNG | Có | 1.15.3 | **AI chính** (Template Deformation) | Thiếu trong requirements.txt. |
| `cv2` (opencv-python) | KHÔNG | Có | 4.11.0 | **AI chính** (Deformation/Texture) | Thiếu trong requirements.txt. |
| `clip` (OpenAI CLIP) | KHÔNG | Có | 1.0 | **AI chính** (Template Recognition) | Thiếu trong requirements.txt; cài qua git OpenAI/CLIP. |
| `transformers` | KHÔNG | Có | 4.38.2 | **AI chính** (DPT depth, Relief 2.5D) | Thiếu trong requirements.txt. |
| `faiss` (faiss-cpu) | KHÔNG | Có | 1.14.3 | **AI chính** (Template Retrieval) | Thiếu trong requirements.txt. |
| `requests` | KHÔNG | Có | 2.34.2 | **AI chính** (Tripo API) | Thiếu trong requirements.txt. |
| `tsr` (TripoSR) | KHÔNG | Có | — (local package) | **AI chính** (Local TripoSR) | Thiếu trong requirements.txt; là thư viện nội bộ `tsr/`. |
| `gradio_client` | KHÔNG | **KHÔNG** | — | **Tùy chọn** (HF Space pipeline) | `ModuleNotFoundError`. → pipeline HuggingFace không khả dụng trên máy này. |
| `struct`, `json`, `os`, `sqlite3`, `uuid`, `werkzeug`, `shutil`, `math`, `time` | — (stdlib) | — | built-in | **Bắt buộc web** | OK. |

### A.3 Phân loại dependency
- **Bắt buộc để chạy web cơ bản:** `flask`, `pymysql`, `PIL`, `rembg`, `numpy`.
- **Bắt buộc cho pipeline AI chính (demo tối thiểu không cần):**
  - Local TripoSR: `torch`, `tsr`, `trimesh`, `open3d`, `numpy`.
  - Template Retrieval: `torch`, `clip`, `faiss-cpu`, `scipy`, `cv2`, `trimesh`, `numpy`.
  - Relief 2.5D: `torch`, `transformers`, `trimesh`, `numpy`.
  - Tripo API: `requests`.
- **Tùy chọn / chưa khả dụng:** `gradio_client` (pipeline Hugging Face Space).

### A.4 Xung đột / rủi ro phiên bản
1. **NumPy 2.4.6 (thực tế) vs 1.24.3 (khai báo)** — Mức nguy cơ: **Cao**. NumPy 2.x có breaking changes (vd `np.float_` bị gỡ, `copy=False` ngữ cảnh mới). rembg/transformers có thể sinh warning hoặc lỗi runtime ở một số nhánh code.
2. **Flask 3.1.3 (thực tế) vs 2.3.3 (khai báo)** — Mức nguy cơ: **Trung bình**. Code hiện chạy OK, nhưng khai báo sai khiến người cài mới sẽ nhận Flask 3.x (vì pip sẽ lấy bản được khớp với Python 3.11), khác docs cũ.
3. **`clip` không có trên PyPI** — Phải cài qua `pip install git+https://github.com/openai/CLIP.git`, không bổ sung được bằng dòng `clip==x.y` bình thường trong requirements.txt.
4. **`tsr` là package nội bộ** trong `tsr/` của repo (README gọi là TripoSR), không phải pip package.

---

## B. Xác minh từng pipeline

Legend:
- **Có code**: có hiện thực trong source.
- **Dependency/weights sẵn sàng**: môi trường + trọng số + index có mặt trên máy.
- **Đã chạy thật**: có log không lỗi + file đầu ra (GLB/OBJ/PLY) được tạo trong lần test này hoặc có bằng chứng xác đáng.
- **Bằng chứng**: đường dẫn artifact / log / status code.

| Pipeline | Có code | Dependency/weights sẵn sàng | Đã chạy thật | Bằng chứng | Kết luận |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **rembg (tách nền)** | Có (`services/bg_remover.py`) | Có (`rembg` 2.0.52, U-2-Net model tự tải cache) | **Có** | `POST /api/bg-remove` HTTP 200, file `/static/uploads/asset_8e48..._nobg.png` được tạo, pipeline elliptical sau đó đọc được nó. Log: `BG-REMOVE: 200`. | **Khả dụng** (cũng có fallback PIL nếu thiếu rembg). |
| **Procedural Elliptical** | Có (`services/mesh_generator.py` `generate_3d_model(style='elliptical')`) | Có (chỉ cần PIL+numpy+struct, không cần GPU/weights) | **Có** | `GEN-3D: 200 elapsed=0.3s`, `method=procedural_elliptical`, vertices=3074, faces=6144. Artifact: `static/models/model_27_333d3d.glb` (153228B), `.obj` (538694B), `.ply` (281511B). Header GLB `0x46546C67 ver=2 length=153228`. trimesh load OK. | **Khả dụng — đã xác minh đầu cuối bằng test thực tế.** |
| **Procedural Relief 2.5D (Extruded)** | Có (`mesh_generator.py::generate_extruded_silhouette`) | Phụ thuộc `transformers` + `Intel/dpt-large` (chưa tải trên máy). | **Chưa** | Không chạy trong lần test (chỉ test elliptical). | **Thử nghiệm** — có thể chạy nếu tải depth model (~1.5GB). |
| **Local TripoSR (GPU)** | Có (`services/local_tripo_service.py`; `tsr.system.TSR`; Open3D Poisson) | `is_available() == True` (torch+CUDA+tsr+ weights `model.ckpt` 1.67GB + `config.yaml`). | **Chưa (trong lần này)** | Không chạy trong lần test theo nguyên tắc an toàn (model nặng, thời gian inference ~25–60s, có thể sinh file lớn). | **Khả dụng về mặt môi trường** — chưa có bằng chứng chạy thật trong báo cáo này (cần xác nhận chạy riêng). |
| **Template Retrieval + Deformation** | Có (`template_service.py` + `recognition_service.py` + `retrieval_service.py` + `deformation_service.py`) | `ts.is_available() == True`. FAISS index 5.7MB, SQLite 13.7MB, 475 template metadata, 101 file .glb trong `static/templates/core_100`. CLIP load OK trên cuda. | **Chưa** | Không chạy generate_3d thực tế qua HTTP trong lần test. Chỉ verify load CLIP + FAISS search metadata không lỗi. | **Khả dụng về mặt môi trường** — chưa chạy full generate (deformation SciPy/Trimesh có thể tốn vài giây). |
| **Tripo API (Cloud)** | Có (`services/tripo_service.py`) | `is_available() == True` — **NHƯNG** API key đang bị **hard-code** trong source. | **Chưa** | Không gọi API thật để tránh tiêu hao quota/lộ key. | **Mã khả dụng nhưng KHÔNG an toàn** — P0 bảo mật. |
| **Hugging Face Space** | Có (`services/hf_service.py`) | `gradio_client` **chưa cài** → `is_available() == False`. | **Không** | `ModuleNotFoundError: No module named 'gradio_client'`. | **Chưa khả dụng trên máy hiện tại.** |

---

## C. Kiểm thử tối thiểu đã chạy (an toàn)

### C.1 Lệnh đã chạy (tóm tắt)
1. Kiểm tra môi trường: `python --version`, `nvidia-smi`, import từng module trong venv.
2. Sinh ảnh mẫu: `scripts/_verify_pipeline.py` tạo `test_apple.png` 256×256 (PIL ellipse đỏ).
3. Khởi động Flask (job nền): `venv\Scripts\python.exe app.py` → log ghi sqlite fallback.
4. Test end-to-end pipeline elliptical qua HTTP: `scripts\_verify_pipeline.py`.
5. Test download 3 file + API asset detail: `scripts\_verify_download.py`.
6. Kiểm tra header GLB + trimesh load: `python -c "import trimesh; trimesh.load('static/models/model_27_333d3d.glb')"`.

### C.2 Kết quả
- **Khởi động Flask:** OK. `GET /` → HTTP 200, content-len 37761. `GET /api/assets` → HTTP 200.
- **Upload:** `POST /api/upload` → HTTP 200, `success=true`, `asset_id=27`.
- **Tách nền (rembg):** `POST /api/bg-remove` → HTTP 200, sinh file `asset_..._nobg.png`.
- **Sinh 3D (procedural_elliptical):** `POST /api/generate-3d` → HTTP 200, elapsed 0.3s.
  - `method=procedural_elliptical`, vertices=3074, faces=6144.
  - Glb 153228 B, obj 538694 B, ply 281511 B — tồn tại vật lý trên đĩa.
- **Three.js (mô phỏng phía client):** GLB header `0x46546C67` (glTF magic), version 2, length đúng bằng kích thước file. `trimesh.load` mở được ⇒ loader của Three.js (GLTFLoader) có thể đọc file này.
- **Tải xuống:** `GET /static/models/model_27_333d3d.{glb,obj,ply}` → đều HTTP 200, content-type `application/octet-stream`, số byte khớp dung lượng file vật lý.
- **API chi tiết asset:** `GET /api/assets/27` → HTTP 200, body 674 bytes.

### C.3 Lỗi quan sát được
- Không có lỗi làm crash server trong test pipeline elliptical.
- Cảnh báo: `requirements.txt` không khớp môi trường thật (xem A.4).
- MySQL chưa chạy → fallback SQLite (không phải lỗi, đúng thiết kế).
- `gradio_client` thiếu → pipeline HuggingFace không khả dụng.

### C.4 Artifact đầu ra
- `static/uploads/test_apple.png` (ảnh mẫu đầu vào, 1549 B).
- `static/uploads/asset_8e48ac59004b488a9ab1c223e90232a2_original.png`
- `static/uploads/asset_8e48ac59004b488a9ab1c223e90232a2_nobg.png`
- `static/models/model_27_333d3d.glb` (153228 B)
- `static/models/model_27_333d3d.obj` (538694 B)
- `static/models/model_27_333d3d.ply` (281511 B)
- `scripts/_verify_pipeline.py`, `scripts/_verify_download.py` (script test, tạm).
- `flask.log`, `verify_out.log`, `dl_out.log` (log test).

> **Lưu ý:** Các file `scripts/_verify_*.py` và log chỉ là artifact tạm phục vụ xác minh — cần dọn sạch trước khi nộp bài (xem E).

---

## D. Chốt phạm vi demo khả thi

### D.1 Pipeline chính đề xuất (DUY NHẤT)
**Ảnh đơn → tách nền (rembg) → Procedural Elliptical → hiển thị Three.js → tải GLB.**

Lý do chọn:
- Đã **chạy thật** end-to-end qua HTTP trong lần test này, có file đầu ra xác minh được.
- Không phụ thuộc cloud, không cần tải model nặng, không đụng đến API key.
- Thời gian sinh ≈ 0.3s — an toàn cho demo trực tiếp tại hội đồng.
- Đầu ra GLB hợp lệ chuẩn glTF 2.0, Three.js GLTFLoader đã được trang bị trong `templates/index.html`.

### D.2 Phân loại các pipeline còn lại
- **Fallback đã có code (chưa chạy thật trong báo cáo này):**
  - Procedural Relief 2.5D (Extruded) — cần tải `Intel/dpt-large`.
- **Thử nghiệm (môi trường sẵn sàng, chưa chạy full generate):**
  - Local TripoSR GPU — `is_available()=True`, weights đủ, nhưng chưa có bằng chứng chạy thật.
  - Template Retrieval + Deformation — `is_available()=True`, index/CLIP sẵn, nhưng chưa chạy full.
- **Chưa khả dụng trên máy hiện tại:**
  - Hugging Face Space (`gradio_client` thiếu).
- **Không an toàn — không demo trực tiếp:**
  - Tripo API Cloud — key bị hard-code, cần dọn dẹp bảo mật trước.

---

## E. Danh sách sửa tối thiểu sau xác minh

### P0 — Bảo mật và lỗi không chạy (bắt buộc làm trước)
1. **Xóa Tripo API key hard-code**  
   - File: `services/tripo_service.py` (dòng 12).  
   - Lý do: key thật bị lộ trong source, vi phạm nguyên tắc bảo mật và quy tắc xác minh #4.  
   - Cần: đọc `os.environ.get("TRIPO_API_KEY", "")` (không default key), callback `is_available()` giữ nguyên vì đã kiểm tra truthy.

2. **Tạo `.env.example` (placeholder only) + `.gitignore`**  
   - Files mới: `.env.example`, `.gitignore`.  
   - Lý do: ngăn commit key thật; cung cấp template cấu hình cho người chạy.  
   - `.env.example` nội dung dự kiến:  
     ```
     # Copy to .env and fill real values
     SECRET_KEY=change-me
     TRIPO_API_KEY=
     DB_HOST=localhost
     DB_USER=root
     DB_PASSWORD=
     DB_NAME=3dgame_assets
     ```

3. **Sửa `requirements.txt` cho khớp môi trường thật** (không cài gói nặng mới)  
   - File: `requirements.txt`.  
   - Lý do: hiện trạng sai phiên bản (Flask, numpy) và thiếu toàn bộ gói AI → người khác chạy `pip install -r requirements.txt` sẽ crash.  
   - Phải chốt phiên bản theo môi trường đã chạy OK: Flask 3.1.3, PyMySQL 1.4.6, Pillow 10.0.0, rembg 2.0.52, numpy 2.4.6, và bổ sung torch/trimesh/open3d/scipy/opencv-python/clip(bằng URL git)/transformers/faiss-cpu/requests.  
   - **Cần xác nhận trước khi sửa** (xem mục cuối).

### P1 — Đảm bảo demo chính chạy trên máy hiện tại
4. **Dọn artifact tạm/L=== sau test**  
   - Files: `scripts/_verify_pipeline.py`, `scripts/_verify_download.py`, `flask.log`, `verify_out.log`, `dl_out.log`, và các file `static/uploads/test_apple.png`, `static/uploads/asset_8e48..._*`, `static/models/model_27_333d3d.*`.  
   - Lý do: tránh để file rác và ảnh test lẫn vào nguồn nộp bài; giữ thư viện sạch.  
   - **Cần xác nhận trước khi xóa**.

5. **Khóa pipeline mặc định về "procedural_elliptical" cho demo**  
   - File: `templates/index.html` (dòng 137–141, thẻ `<select id="asset-style-input">`).  
   - Lý do: đảm bảo người dùng demo mở web ra đã chọn đúng pipeline đã được xác minh chạy; tránh vô tình click sang Tripo API (lộ key) hoặc Relief (chưa verify).  
   - **Cần xác nhận trước khi sửa UI** (theo nguyên tắc giai đoạn này không đổi giao diện — đây chỉ là đề xuất, không tự làm).

6. **Kiểm tra kỹ hai pipeline "thử nghiệm" trước demo** (Local TripoSR, Template Retrieval)  
   - Files: `services/local_tripo_service.py`, `services/template_service.py`.  
   - Lý do: đã sẵn sàng về môi trường nhưng chưa có bằng chứng chạy thật; nếu định demo hai pipeline này làm điểm nhấn, cần chạy 1 lần riêng để lấy đầu ra + log.  
   - **Cần xác nhận** xem có muốn chạy xác minh riêng (có thể tốn ~30–60s và vài GB tạm) hay không.

### P2 — Tài liệu, log thực nghiệm, README
7. **Bổ sung log thực nghiệm** (không sửa README.md)  
   - File mới đề xuất: `docs/experiment_log.md` hoặc nhét kết quả vào `Du_Lieu_Nghien_Cuu.xlsx` đã có.  
   - Lý do: ghi lại các bằng chứng chạy (status, time, file size, vertices/faces) để nộp cùng báo cáo.
8. **Sửa README sau giai đoạn này** (theo kế hoạch `AI_AUDIT_REPORT.md` mục 8) —推迟, không làm ở giai đoạn xác minh.

---

## F. Cần xác nhận trước khi sửa
1. **Tripo API key**: xác nhận được phép xóa key hard-code trong `services/tripo_service.py` và chuyển sang đọc biến môi trường (không phá tính năng cloud, chỉ disable khi thiếu env).
2. **`.env.example` + `.gitignore`**: xác nhận được phép tạo hai file mới tại thư mục gốc.
3. **`requirements.txt`**: confirm được phép cập nhật phiên bản cho khớp môi trường đã chạy OK (Flask 3.1.3, numpy 2.4.6, + các gói AI còn thiếu). Cần cho biết có muốn cố định chính xác phiên bản (pin) hay để range (`>=`)?
4. **Dọn dẹp artifact tạm**: confirm được phép xóa `scripts/_verify_*.py`, `flask.log`, `verify_out.log`, `dl_out.log`, và các file test trong `static/uploads/`, `static/models/`.
5. **Mặc định UI pipeline**: có muốn đặt `procedural_elliptical` làm option mặc định của `<select>` trong `templates/index.html` không (sẽ động chạm UI — chỉ làm nếu bạn đồng ý)?
6. **Chạy verify thêm**: có muốn chạy xác minh thực tế Local TripoSR và/hoặc Template Retrieval để lấy bằng chứng đầu ra thật (có thể tốn ~30–60s mỗi pipeline và tạo file GLB lớn vài MB)?
