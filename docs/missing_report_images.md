# Missing Report Images

## Existing Images (in BaoCao_TotNghiep/report_images/)
| File | Status | Source |
|------|--------|--------|
| logo_ctu.png | CÓ | Trường ĐH Cần Thơ |
| h3_2_anh_goc_mau.png | CÓ | GSO render front.png |
| h3_3_anh_tach_nen.png | CÓ | Ảnh sau rembg |
| visual_comparisons.jpg | CÓ | TripoSR source figures (KHÔNG phải từ hệ thống) |
| test_chair_sample.png | CÓ | Test chair upload |

## Missing Images
| Mã | File | Mô tả | Cách tạo |
|----|------|-------|----------|
| H3.1 | h3_1_pipeline_he_thong.png | Sơ đồ pipeline | Vẽ TikZ hoặc draw.io |
| H3.4 | h3_4_giao_dien_tai_anh.png | Screenshot upload | Chụp từ web demo |
| H3.5 | h3_5_trang_thai_suy_luan.png | Screenshot processing | Chụp từ web demo |
| H3.6 | h3_6_viewer_ket_qua.png | Screenshot viewer | Chụp từ web demo |
| H3.7 | h3_7_goc_nhin_asset.png | Ghép nhiều góc | Chụp từ viewer + ghép ảnh |
| H3.8 | h3_8_asset_editor.png | Screenshot editor | Chụp từ web demo |
| H3.9 | h3_9_truoc_sau_chinh_sua.png | Trước/sau chỉnh sửa | Chụp từ web demo |
| H3.10 | h3_10_xuat_tep_asset.png | Screenshot export | Chụp từ web demo |
| GSO input | gso_input_example.png | Ảnh render 1 mẫu GSO | Từ static/templates/gso/*/renders/front.png |
| GSO GT | gso_gt_example.png | Mesh GT GSO | Từ static/templates/gso/*/preview (nếu có) |
| Prediction | gso_pred_example.png | Mesh dự đoán | Từ experiments/outputs/.../preview.png |

## visual_comparisons.jpg Warning
File này được copy từ `TripoSR/figures/visual_comparisons.jpg` - là ảnh từ bài báo TripoSR gốc, KHÔNG phải kết quả từ hệ thống. Cần thay thế bằng ảnh thật từ pilot GSO.
