# HƯỚNG DẪN CHI TIẾT: Benchmark đa mô hình trên Google Colab

Phiên bản: 2026-08-11 · Pha C1.5 · Chế độ hướng dẫn thủ công (không tự động hóa trình duyệt)

---

## 0. Tổng quan

Bạn sẽ chạy 3 mô hình tạo 3D từ ảnh trên cùng 29 ảnh vật thể (GSO) mà nghiên cứu C1 đã dùng,
đánh giá bằng đúng bộ đánh giá của C1. Kết quả dùng cho phần **so sánh mô hình** trong luận văn.

| # | Notebook | Mô hình | Trọng số (tải tự động) | Thời gian dự kiến |
|---|---|---|---|---|
| 00 | `00_prepare_dataset.ipynb` | — (tiền xử lý) | rembg u2net | 10–15 phút |
| 01 | `01_triposr_t4_benchmark.ipynb` | TripoSR | `stabilityai/TripoSR` (~1,7 GB) | smoke ~2 phút + batch ~1,5–2 giờ |
| 02 | `02_instantmesh_t4_benchmark.ipynb` | InstantMesh large | `TencentARC/InstantMesh` + `sudo-ai/zero123plus-v1.2` (~5 GB) | smoke ~2 phút + batch ~2–3 giờ |
| 03 | `03_hunyuan3d2mini_t4_benchmark.ipynb` | Hunyuan3D-2mini | `tencent/Hunyuan3D-2mini` (~3 GB) | smoke ~1 phút + batch ~1,5–2 giờ |
| 05 | `05_validate_and_package_results.ipynb` | — (kiểm tra) | — | 5 phút |

**Quy trình bắt buộc (mỗi notebook mô hình):** chạy **smoke test 1 ảnh → DỪNG → gửi kết quả cho người hướng dẫn → được duyệt → mới chạy batch 29 ảnh.**

> ⚠️ 3 quy tắc vàng:
> 1. **Không sửa code** trong notebook.
> 2. Cell nào lỗi → **chụp màn hình đầy đủ** gửi về, chờ hướng dẫn. Không tự sửa lung tung.
> 3. Chỉ chạy **1 notebook tại 1 thời điểm**, chạy lần lượt theo thứ tự 00 → 01 → 02 → 03 → 05.

---

## 1. Chuẩn bị (làm 1 lần, ~10 phút)

### 1.1. Tài khoản Google
Cần tài khoản Google (Gmail) bất kỳ để dùng Google Drive + Colab. Nếu chưa có → đăng ký tại https://accounts.google.com.

### 1.2. Lấy 2 file dữ liệu gốc (đã đóng gói sẵn)
Trên máy tính, 2 file này nằm ở:
```
E:\xampp\htdocs\3DGame\experiments\multimodel\package\
├── gso29_standardized.zip      (4,2 MB — 29 ảnh RGBA 512×512 đã chuẩn hóa)
└── standardized_manifest.csv   (SHA-256 từng ảnh + hash input C1 để đối chiếu)
```

> Vì sao không cần file ảnh gốc/rembg: việc tách nền (rembg u2net) phải dùng **đúng phiên bản
> 2.0.52 của nghiên cứu C1**, nhưng Colab hiện dùng Python 3.12+ nên **không cài được rembg 2.0.52**.
> Vì vậy toàn bộ bước tiền xử lý đã được chạy sẵn trên máy nguồn (kết quả trùng pixel 100% với
> input C1 — 29/29 PASS) và đóng gói vào `gso29_standardized.zip`. Colab chỉ cần kiểm tra SHA-256.

### 1.3. Tạo cây thư mục trên Google Drive
1. Vào https://drive.google.com (đăng nhập tài khoản Google).
2. Bấm **Mới → Thư mục mới** (hoặc **+ Mới → Thư mục**), đặt tên chính xác:
   `nien_luan_3d_benchmark`
3. Mở thư mục vừa tạo → tạo thư mục con `dataset` → bên trong `dataset` tạo tiếp `package`.
4. Vào thư mục `package` → bấm **+ Mới → Tải tệp lên** → chọn cả 2 file ở mục 1.2.
   Kết quả phải là:
   ```
   MyDrive/nien_luan_3d_benchmark/
   └── dataset/
       └── package/
           ├── gso29_standardized.zip
           └── standardized_manifest.csv
   ```
5. **Kiểm tra lại kỹ tên thư mục** — viết đúng chính tả, không dấu: `nien_luan_3d_benchmark`.

> Lưu ý: Các notebook sẽ **tự tạo** các thư mục `dataset/source`, `dataset/standardized_rgba`,
> `dataset/adapters`, `runs/` bên trong `nien_luan_3d_benchmark` — bạn không cần tạo trước.

---

## 2. Cách mở Colab và chọn GPU T4

1. Vào https://colab.research.google.com bằng trình duyệt Chrome (nên dùng Chrome, không dùng Edge/private window).
2. Đăng nhập cùng tài khoản Google.
3. Bấm **Tệp (File) → Mở sổ ghi chú (Open notebook) → Tải lên (Upload)** → chọn file
   `E:\xampp\htdocs\3DGame\colab\00_prepare_dataset.ipynb`.
   (Có thể kéo-thả file `.ipynb` thẳng vào cửa sổ Colab.)
4. Chọn GPU T4: menu trên cùng **Runtime → Change runtime type → Accelerator = GPU (T4)** → **Save**.
   - Nếu không thấy "T4" mà chỉ thấy "GPU" → vẫn chọn **GPU** (thực tế Colab thường cấp T4).
   - ⚠️ Với notebook **00 và 05** không cần GPU nhưng vẫn có thể để GPU — không sao.
5. Sau khi chọn xong, bấm nút **▶ Run all** ở đầu notebook **KHÔNG được dùng**.
   Bạn sẽ chạy **từng cell một**: bấm vào ô code, nhấn **Shift+Enter** để chạy cell đó.

**Cách chạy từng cell (bắt buộc làm đúng):**
- Bấm chuột vào cell → nhấn **Shift+Enter** → chờ cell chạy xong (dấu ✔ xanh hiện trái cell).
- Đọc kỹ kết quả in ra trước khi sang cell tiếp theo.
- Cell nào đang chạy: dấu ⏳ xoay vòng. Muốn dừng giữa chừng: bấm **Runtime → Interrupt**.

---

## 3. Notebook 00 — Chuẩn bị tập dữ liệu

Mục đích: giải nén 29 ảnh chuẩn hóa (đã làm sẵn trên máy nguồn), kiểm tra SHA-256,
tạo ảnh đầu vào (adapter) riêng cho từng mô hình. **Colab không cần rembg.**

### Cell theo thứ tự

| Cell | Việc của bạn | Kết quả mong đợi |
|---|---|---|
| PHẦN 1 - Mount Drive | Chạy → bấm link → đăng nhập → **copy mã xác nhận** → dán vào ô → Enter | In chữ "Mounted at /content/drive" |
| Cell "Tao thu muc" | Chạy | In 2 dòng `zip ok : True` và `manifest ok: True` (đều `True`) |
| Giải nén + SHA-256 | Chạy | `TAT CA PASS. Sang phan 2.` |
| PHẦN 2 - tạo adapter | Chạy | In `Tao adapter xong: 29/29 success` |
| PHẦN 3 - xác minh hash | Chạy | In `standard_input_hash_match: PASS=29 / 29` |

### Nếu gặp
- **Cell nào in FAIL/ERROR** → chụp toàn màn hình (mục 8.1) gửi về. Không sang cell tiếp.
- Hết thời gian phiên (runtime bị ngắt) giữa chừng → mở lại notebook, chạy lại từ PHẦN 1
  (các file đã tạo trên Drive vẫn còn; cell nào đã có kết quả đúng thì có thể bỏ qua sau khi xác nhận).

**Xong 00** → chụp màn hình dòng `PASS=29/29` lưu lại, mở notebook 01.

---

## 4. Notebook 01 — TripoSR

Mở như mục 2 (Tệp → Mở sổ ghi chú → Tải lên).

### 4.1. Chạy theo thứ tự

| Cell | Kết quả mong đợi |
|---|---|
| PHẦN 1 | Bảng `nvidia-smi` + `GPU: Tesla T4` |
| PHẦN 2 - Mount Drive | `Mounted at /content/drive` |
| Cell RUN_ID | In `RUN_ID: triposr_t4_<giờ chạy>` |
| Cell manifest | `Manifest tren Drive: 29 objects` + `Thieu adapter: khong co` |
| Clone + checkout | `git rev-parse HEAD` in đúng `107cefdc244c39106fa830359024f6a2f1c78871` |
| pip install | `deps ok` |
| Tải checkpoint + xác minh | In 2 dòng SHA-256 + `CHECKPOINT TRUNG KHAI - ok.` |
| Nạp mô hình | `model load time_s: ~10–30` |
| Cell hàm run_one | `Ham da san sang.` |
| **SMOKE TEST** | Bảng chi tiết kết thúc bằng `SMOKE: SUCCESS` |

### 4.2. ⛔ DỪNG SAU SMOKE — QUY TRÌNH DUYỆT BẮT BUỘC

1. Chụp toàn màn hình từ PHẦN 1 đến hết cell SMOKE TEST.
2. Gửi về (theo kênh đang trao đổi), kèm:
   - run_id (ví dụ `triposr_t4_20260811_153000`);
   - GPU được cấp;
   - thời gian inference, VRAM, `SMOKE: SUCCESS` hay FAIL;
   - nếu có dòng `LUU Y`/cảnh báo khác thì ghi rõ.
3. **Chờ người hướng dẫn trả lời "duyệt chạy batch"** rồi mới sang mục 4.3.
   Mọi lỗi ở smoke sẽ được xử lý từng bước trước khi chạy batch.

### 4.3. PHẦN 5 — Batch 29 ảnh (chỉ sau khi duyệt)

- Chạy cell "Batch 29 ảnh" → chờ chạy xong (~1,5–2 giờ). Mỗi ảnh in 1 dòng `OK`.
- Trong lúc chạy: **không tắt tab, không tắt máy, không mở notebook khác**.
- Cell cuối: in `success=29 fail=0` + đường dẫn zip.

**Nếu runtime bị mất giữa chừng** (thông báo "Runtime disconnected" hoặc nút ▶ mất chữ):
1. Mở lại cùng notebook.
2. Chạy lại lần lượt: PHẦN 1 (kiểm tra GPU), mount Drive, cell RUN_ID (**giữ nguyên tên như cũ** —
   nếu RUN_ID mới khác thì các ảnh cũ coi như bỏ, phải báo lại!), cell manifest.
3. Chạy lại PHẦN 3 (clone + cài đặt + checkpoint) và PHẦN 4 (nạp mô hình).
4. Chạy lại cell Batch → các ảnh đã xong sẽ in `SKIP (da xong)`.
5. Chụp màn hình gửi về.

---

## 5. Notebook 02 — InstantMesh và Notebook 03 — Hunyuan3D-2mini

Lặp lại **y hệt** quy trình mục 4 với commit/lần chạy tương ứng:

| | 02 InstantMesh | 03 Hunyuan3D-2mini |
|---|---|---|
| Commit hiển thị ở `git rev-parse HEAD` | `08822c52fdc399b93ea00e4fa9e596344ed52ccc` | `f8db63096c8282cb27354314d896feba5ba6ff8a` |
| Thời gian cài đặt (PHẦN 3) | 3–8 phút (biên dịch kernel) | 3–6 phút |
| Smoke | `SMOKE: SUCCESS` + dòng `dominant_axis` | `SMOKE: SUCCESS` + dòng `dominant_axis` |

**Lưu ý riêng notebook 02:** InstantMesh cần nhiều VRAM (~12–14 GB) — nếu smoke test chết
giữa chừng với lỗi `out of memory`, dừng lại và gửi ảnh màn hình (có phương án xử lý riêng,
không tự ý giảm bước/đổi config).

**Lưu ý riêng notebook 03:** lần đầu `from_pretrained` tải ~3 GB trọng số — chờ cho xong.
Nếu thấy lỗi liên quan `hunyuan3d` hoặc `hy3dgen` → gửi nguyên văn lỗi (cuộn hết ô lỗi đỏ).

---

## 6. Notebook 05 — Kiểm tra và đóng gói kết quả

1. Mở notebook 05, chạy mount Drive.
2. Cell thứ 2: in bảng các run đã chạy trên Drive — tất cả phải có trạng thái **OK**, success=29, meshLoi=0.
3. Cell thứ 3: in danh sách zip + hướng dẫn tải về.
4. **Tải từng zip về máy**: bên trái Colab bấm biểu tượng 📁 (thư mục) → mở
   `drive/MyDrive/nien_luan_3d_benchmark/runs/<run_id>/` → chuột phải file `<run_id>.zip` → **Download**.
   Lưu vào:
   ```
   E:\xampp\htdocs\3DGame\experiments\multimodel\raw\<run_id>\<run_id>.zip
   ```
   Giải nén zip ngay trong thư mục đó (nội dung: `run_log.csv`, `metadata.json`, `meshes/*.glb`).
5. Chụp màn hình 2 cell kết quả gửi về.

**Bước tiếp theo (người hướng dẫn sẽ gửi hướng dẫn riêng):** chạy
`python -m scripts.benchmark.verify_multimodel_results` trên máy để kiểm tra lần cuối,
sau đó đánh giá chất lượng bằng `evaluate_mesh.py` (giao thức C1) rồi tổng hợp số liệu.

---

## 7. Thời gian và mức tiêu thụ ước tính (thông tin tham khảo)

- Mỗi phiên Colab miễn phí thường chạy được **2–4 giờ liên tục** (có thể ít hơn khi bận).
- Nếu runtime hết giờ giữa batch → thực hiện resume như mục 4.3 (mỗi lần mở lại phải cài lại repo/trọng số).
- Khuyến nghị: chạy 01 vào buổi sáng, 02 vào buổi chiều, 03 vào buổi tối (tránh tải cao điểm).
- Kiểm tra mức dùng GPU trong lúc chạy (tùy chọn): nút **Chrome → ⋮ → Dùng tab cũng cấp…**
  không bắt buộc; không cần theo dõi.

---

## 8. Lỗi thường gặp và cách xử lý

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| "KHONG CO CUDA" | Chưa chọn GPU | Runtime → Change runtime type → GPU → Save → mở lại notebook (File → Reload) |
| Cell chạy mãi không xong (>15 phút) | Đang tải trọng số lần đầu | Chờ; kiểm tra dòng "Downloading" có nhảy % không |
| "out of memory" ở notebook 02 | VRAM T4 đủ nhưng bị chiếm bởi phiên khác | Dừng các notebook/phiên khác; mở lại notebook; nếu vẫn lỗi → gửi ảnh |
| "Runtime disconnected / expired" | Hết thời gian phiên | Resume theo mục 4.3; **báo lại RUN_ID thực tế** |
| `zip ok : False` / `manifest ok: False` | Chưa upload hoặc upload sai tên | Kiểm tra lại tên 2 file trong `dataset/package/` (mục 1.3) |
| Cell "Giải nén + SHA-256" in FAIL | File tải lên bị hỏng/không đúng bản | Xóa file trong Drive `dataset/package`, tải lại 2 file từ mục 1.2 |
| `standard_input_hash_match = FAIL` | File hỏng hoặc adapter sai | **Dừng**, gửi ảnh màn hình cell PHẦN 3 (xử lý riêng) |
| Lỗi màu đỏ ở pip install | Xung đột phiên bản (Python 3.12 của Colab) | Chụp **cả khối lỗi** gửi về; không tự nâng cấp thêm gói |
| "Mounted at /content/drive" không hiện | Chưa dán mã xác nhận | Chạy lại cell mount, làm đúng 4 bước mục 3 |

**Nguyên tắc chung khi gặp bất kỳ lỗi nào:** dừng ngay, chụp ảnh, gửi về, chờ hướng dẫn.
Người hướng dẫn sẽ đưa **một phương án** duy nhất để bạn thử; nếu vẫn lỗi sẽ đưa phương án kế tiếp.

### 8.1. Cách chụp màn hình đầy đủ (bắt buộc)
- Windows: **Windows + Shift + S** → kéo vùng chọn cả notebook (từ đầu đến hết lỗi) → dán vào khung chat.
- Hoặc chụp cả màn hình: **PrtScn** → dán.
- Chụp **từ cell PHẦN 1** trở xuống để người hướng dẫn thấy GPU và phần lỗi trong cùng 1 ảnh.
- Với lỗi dài: copy văn bản lỗi (bấm vào khối lỗi đỏ → Ctrl+A → Ctrl+C) dán vào chat kèm ảnh.

---

## 9. Câu hỏi thường gặp

**Q: Colab báo lỗi "Ignored versions... Requires-Python" khi cài rembg thì sao?** Đã xử lý xong:
notebook 00 **không còn cài rembg** — ảnh chuẩn hóa được làm sẵn trên máy nguồn bằng rembg 2.0.52
(29/29 trùng pixel với input C1). Các notebook 01–03 cũng đã bỏ `requirements.txt` của repo
(tránh pin torch cũ không tương thích Python 3.12); chỉ cài các gói cần thiết theo tên.

**Q: Em cần trả phí không?** Không. Colab miễn phí đủ chạy cả 3 mô hình (T4 16 GB).

**Q: Chạy 2 notebook cùng lúc có nhanh hơn không?** Không — Colab miễn phí chỉ cho 1 GPU/phiên.
Chạy lần lượt.

**Q: Sao phải chạy smoke test trước?** Để phát hiện lỗi cấu hình/model/hash trước khi đốt
~2 giờ chạy batch. Nếu smoke hỏng thì batch cũng hỏng.

**Q: Em tắt máy giữa chừng được không?** Phiên Colab chạy trên server của Google — tắt máy không
làm dừng phiên, nhưng **không nên**: nếu mất kết nối lâu, phiên có thể bị ngắt → chạy lại theo resume.

**Q: Các file kết quả lưu ở đâu?** Trên Google Drive trong
`nien_luan_3d_benchmark/runs/<run_id>/` (và bản zip ngay trong thư mục run). Tải về máy theo mục 6.

**Q: Nếu em cần chạy lại cả batch từ đầu?** Chỉ khi có yêu cầu từ người hướng dẫn (thường do lỗi
nghiêm trọng). Xóa folder run tương ứng trên Drive rồi chạy lại — **chỉ làm khi được yêu cầu**.

---

## 10. Checklist cuối cùng (gửi về khi hoàn thành tất cả)

- [ ] Notebook 00: `PASS=29/29` (ảnh chụp)
- [ ] Notebook 01: smoke SUCCESS + batch `success=29 fail=0` (ảnh chụp, ghi run_id)
- [ ] Notebook 02: smoke SUCCESS + batch `success=29 fail=0` (ảnh chụp, ghi run_id)
- [ ] Notebook 03: smoke SUCCESS + batch `success=29 fail=0` (ảnh chụp, ghi run_id)
- [ ] Notebook 05: bảng tóm tắt toàn OK + 3 zip đã tải về đúng thư mục `experiments/multimodel/raw/`
