# SELECTION GUIDE — Chọn Template core_100

## Mục tiêu

Chọn **20–40 template** từ bộ core_100 (101 file GLB) để giữ lại cho web demo giáo dục 3D. Các template được chọn sẽ làm thư viện nguồn cho CLIP Template Retrieval.

## Tiêu chí ưu tiên

### Giữ lại (KEEP) — template phù hợp

- **Rubik / Cube / Khối hình học**: đồ chơi trí tuệ, xoay rubik, khối lập trình.
- **Vật dụng học tập**: bàn ghế, bảng đen, sách vở, bút, compa, thước kẻ.
- **Vật thể đơn giản, rõ ràng**: quả táo, quả bóng, hình khối cơ bản.
- **Đồ chơi giáo dục**: xe đồ chơi, máy bay, robot nhỏ, con vật.
- **Mô hình sinh học**: bộ xương, nội tạng (tim, não, phổi), tế bào — nếu hình dạng rõ và polycount phù hợp.
- **Cấu trúc kiến trúc đơn giản**: cầu, tháp, nhà — nếu polycount thấp (< 50K faces).
- **Công cụ, dụng cụ**: kéo, búa, tua vít, kính hiển vi.

### Loại bỏ (REMOVE) — template không phù hợp

- **Nhân vật phức tạp** (người, động vật chi tiết) — polygon cao, không liên quan giáo dục.
- **Vũ khí, bạo lực**: súng, dao, kiếm.
- **Phương tiện phức tạp**: xe hơi chi tiết, tàu chiến, máy bay phản lực.
- **Mô hình siêu chi tiết** (> 200K faces) — nặng, chậm trên web.
- **File lỗi** (không hiển thị, thiếu texture, mesh rỗng).
- **File trùng lặp** (cùng object với tên khác).
- **Chủ đề không liên quan**: ma quái, giả tưởng, vũ trụ, văn hóa đại chúng.

### Cần xem xét (REVIEW) — chưa quyết định

Giữ nguyên trạng thái `REVIEW`, sau đó xem thumbnail và quyết định.

## Hướng dẫn thao tác

1. Mở `docs/template_catalog/index.html` trong trình duyệt.
2. Dùng ô tìm kiếm và bộ lọc danh mục để duyệt.
3. Mở `docs/template_catalog/template_inventory.csv` bằng Excel / Google Sheets / Notepad++.
4. Với mỗi template, điền vào cột `keep_for_education`:
   - `KEEP` — giữ lại cho web demo
   - `REMOVE` — không dùng
   - `REVIEW` — chưa chắc (mặc định)
5. Cột `notes` có thể ghi chú lý do (không bắt buộc).
6. Lưu file CSV.

## Lưu ý quan trọng

- **KHÔNG xóa file GLB khỏi `static/templates/core_100/` ở giai đoạn này.**
- Việc xóa template sẽ được thực hiện sau khi có danh sách KEEP/REMOVE hoàn chỉnh.
- Nếu template có thumbnail trống hoặc lỗi, mở GLB trực tiếp bằng [glTF Viewer](https://gltf-viewer.donmccurdy.com/) hoặc Babylon.js Sandbox để kiểm tra.
- Bộ sưu tập được lấy từ Objaverse, giấy phép CC-BY-4.0.

## Ước lượng số lượng

| Loại | Số lượng gợi ý |
|------|---------------|
| KEEP | 20–40 |
| REMOVE | 40–70 |
| REVIEW | còn lại |

Sau khi có danh sách KEEP, pipeline CLIP Template Retrieval sẽ chỉ search trên subset đã chọn.
