# Missing GSO Geometry Evidence

## Current Status
Chưa thể tính các metric hình học định lượng (Chamfer Distance, F-score, Precision, Recall, Normal Consistency) cho 10 mẫu GSO pilot.

## Lý do
1. **Chưa căn chỉnh hệ tọa độ**: Prediction mesh từ TripoSR và ground truth mesh GSO có hệ tọa độ khác nhau (center, scale, orientation).
2. **Chưa có protocol chuẩn hóa**: Cần thống nhất:
   - Chuẩn hóa tâm (center to origin)
   - Chuẩn hóa tỉ lệ (scale to unit sphere hoặc bounding box diagonal)
   - Xử lý rotation (align principal axes hoặc dùng ICP)
3. **Chưa kiểm tra topology**: Một số prediction mesh có thể có non-manifold edges hoặc self-intersections.

## Required Steps
1. Chuẩn hóa tâm của prediction và GT mesh
2. Chuẩn hóa tỉ lệ (scale sao cho bounding box diagonal = 1 hoặc 2)
3. Căn chỉnh rigid (ICP) nếu cần
4. Surface sampling 50,000-100,000 điểm
5. Tính CD, Precision, Recall, F-score
6. Tính Normal Consistency nếu normal vector hợp lệ

## Script
`evaluate_geometry.py` đã được tạo (draft) tại thư mục gốc dự án, cần kiểm tra và chạy thử.

## Trong main.tex
Chương 4 ghi rõ: "Chưa đánh giá hình học định lượng do thiếu ground truth được căn chỉnh."
