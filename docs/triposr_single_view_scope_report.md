# TripoSR Single-View Scope Report

## Vấn đề

TripoSR Offline (`local_tripo_service.py`) cho phép upload tối đa 6 ảnh (Front, Back, Left, Right, Top, Bottom) nhưng **chỉ dùng đúng 1 ảnh đầu tiên** (Front/MAIN) để sinh mesh. Các ảnh góc khác được tải lên, tách nền, lưu database nhưng không ảnh hưởng tới kết quả 3D.

## Nguyên nhân gốc

- TSR model (`tsr/system.py:87-120`) xử lý mỗi ảnh INDEPENDENTLY, không có cơ chế fusion multi-view.
- `extract_mesh()` luôn lấy `meshes[0]` (`local_tripo_service.py:92`).
- Output 1 ảnh vs 4 ảnh: giống hệt (48,870 raw verts → 117,764 processed, vertex colors preserved).

## Các thay đổi đã thực hiện (2026-07-19)

### 1. Pipeline honesty — JSON response (`services/local_tripo_service.py:230-256`)

| Key cũ | Key mới | Ý nghĩa |
|--------|---------|---------|
| — | `uploaded_image_count` | Số ảnh người dùng tải lên |
| — | `preprocessed_image_count` | Số ảnh qua rembg thành công |
| — | `model_fusion_image_count: 1` | Số ảnh thực tế model fusion (luôn 1) |
| — | `used_views: ["front"]` | Ảnh nào được dùng |
| — | `ignored_views: [...]` | Ảnh nào không được dùng |

### 2. UI honesty (`templates/index.html:140` + `static/js/app.js`)

- Note vàng dưới style select khi chọn TripoSR:
  > "TripoSR Offline hiện sử dụng ảnh Front/MAIN để sinh mesh. Các ảnh góc khác được lưu để phục vụ phương pháp hỗ trợ trong tương lai."
- Metric row "Ảnh đầu vào / đã dùng" hiển thị `3 ảnh tải lên, 1 ảnh dùng (front)`.

### 3. Docs honesty

- `docs/multiview_trace_report.md`: cập nhật keys trung thực.
- `docs/multiview_triposer_comparison.md`: cập nhật keys + thêm UI fix.

## Hạn chế hiện tại

- Upload nhiều ảnh vẫn giữ nguyên để phục vụ CLIP Template Retrieval (dùng multi-view) và tương lai.
- TripoSR local không thể fusion multi-view do giới hạn kiến trúc TSR model.
- Nếu user upload 1 ảnh hoặc 6 ảnh, output TripoSR hoàn toàn như nhau.

## Khuyến nghị tương lai

1. Chặn upload nhiều ảnh khi chọn TripoSR (UI chỉ cho 1 slot).
2. Hoặc tích hợp model multi-view thực sự (InstantMesh, Zero123++, Unique3D).
3. Hoặc fine-tune TSR với multi-view conditioning.
