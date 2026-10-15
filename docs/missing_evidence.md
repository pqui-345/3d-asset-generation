# Missing Evidence Log

## Figures
- **h3_1_pipeline_he_thong.png**: Sơ đồ pipeline hệ thống (ảnh → rembg → TripoSR → GLB → viewer/editor). Cần vẽ bằng draw.io, Inkscape hoặc TikZ.
- **h3_4_giao_dien_tai_anh.png**: Screenshot giao diện upload ảnh. Cần chụp từ web demo.
- **h3_5_trang_thai_suy_luan.png**: Screenshot khi đang xử lý (có thể là log hoặc progress indicator).
- **h3_6_viewer_ket_qua.png**: Screenshot viewer với mesh đã nạp.
- **h3_7_goc_nhin_asset.png**: Ghép 2–3 góc nhìn asset từ viewer.
- **h3_8_asset_editor.png**: Screenshot editor + control panel.
- **h3_9_truoc_sau_chinh_sua.png**: So sánh trước/sau chỉnh sửa.
- **h3_10_xuat_tep_asset.png**: Screenshot export dialog hoặc danh sách file.

## Experiments
- **E1** (tách nền vs không tách nền): Chưa chạy.
- **E2** (hiển thị và xuất): Chưa chạy bài bản.
- **E3** (loại vật thể dễ/khó): Chưa chạy.
- **E4** (editor): Chưa chạy.
- **Phân loại (SVM/RF/ResNet/ViT)**: Chưa triển khai do thiếu dữ liệu ảnh render.

## Metrics
- Chamfer Distance: Chưa tính (thiếu GT aligned).
- F-score: Chưa tính.
- Normal Consistency: Chưa tính.
- Classification accuracy: Chưa có.

## Code
- `evaluate_geometry.py`: Chưa tạo (chỉ có draft protocol).
- Script căn chỉnh prediction-GT: Chưa có.
- Script render ảnh từ mesh: Chưa có.
