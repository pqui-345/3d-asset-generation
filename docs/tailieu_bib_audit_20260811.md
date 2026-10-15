# Audit tài liệu tham khảo (tailieu.bib) — báo cáo

Ngày: 2026-08-11 | File: `baocao/tailieu.bib` (553 dòng) | Tổng cộng: **60 entries**

## 1. Tóm tắt
- 60 entries, toàn bộ 60 được trích dẫn (`\cite`) trong `main.tex`.
- Không trùng key, không trùng DOI.
- Cấu trúc BibTeX hợp lệ (mỗi entry đủ trường author/title/journal|booktitle/year/doi).

## 2. Phân loại theo mức độ liên quan đến đề tài (3D reconstruction từ 1 ảnh)
| Nhóm | Số lượng | Ghi chú |
|---|---|---|
| A. Lõi — mô hình single-image-to-3D | 19 | TripoSR, InstantMesh, Wonder3D, Zero123++, One-2-3-45, SyncDreamer, MVDream, LGM, DreamGaussian, Point-E, DreamFusion, LRM, Shap-E, Zero-1-to-3, Open3D (thư viện), Mesh R-CNN (fan_point_2017), PointNet/PointNet++, DeepSDF, Occupancy Networks, Pixel2Mesh, 3D-R2N2, DISN, Pix2Vox, MarrNet, 3D ShapeNets, TextureNet... |
| B. Dataset | 4 | GSO (downs_google_2022), ShapeNet, Pix3D, OmniObject3D, Objaverse-XL (5) |
| C. Nền tảng chung — kiến trúc/độ đo/thư viện | ~12 | ViT, ResNet, NeRF, 3DGS, DMTet, SVM, KNN, RandomForest, HOG, DINO(ẩn)... |
| D. Khảo sát / ứng dụng (heavy rain → AR giáo dục, HPB surgery...) | ~18 | Survey + ứng dụng; giữ nguyên, dùng ở phần giới thiệu/tổng quan mở rộng |

## 3. Thiếu sót cần bổ sung (khi biên tập chương 2)
| Cần thêm | Entry đề xuất | Lý do |
|---|---|---|
| Hunyuan3D 1.0 | `yang_hunyuan3d_2024` (arXiv:2411.02293) | Đại diện thế hệ mới nhất, có bảng CD/F-score so sánh với TripoSR |
| CRM | `wang_crm_2024` (arXiv:2403.05034, ECCV 2024) | Đại diện nhóm CNN feed-forward (U-Net + Flexicubes), ~10 s |

Nội dung hai entry nằm sẵn ở `baocao/patch_bibtex_suggestions.bib` — copy vào
`tailieu.bib` khi cần; **không chỉnh sửa tailieu.bib trong phạm vi Pha C1**.

## 4. Lỗi nhỏ (không gây lỗi biên dịch)
| Entry | Vấn đề | Đề xuất |
|---|---|---|
| `chen_survey_2026` | Key ghi "2026" nhưng year=2024, bài "A Survey on 3D Gaussian Splatting" (arXiv:2401.03890) | Đổi key thành `chen_survey_2024` hoặc sửa year — chọn 1 chỗ, giữ đồng nhất |
| `zhirong_wu_3d_2015`, `downs_google_2022`, `deitke_objaverse-xl_2023`, `leibe_3d-r2n2_2016`... | DOI dùng `10.48550/arXiv...` cho bài có bản in hội nghị chính thức (CVPR/ICRA/NeurIPS/ECCV) | Có thể thay DOI chính thức (ví dụ 3D ShapeNets có DOI chuẩn) nếu muốn chất lượng hơn; không bắt buộc |
| `kitayama_hog_2019` | arXiv preprint, chưa rõ bản duyệt | Giữ nguyên; chấp nhận preprint |
| `tang_dreamgaussian_2023`, `liu_syncdreamer_2023`... | Preprint arXiv | Giữ nguyên; một số đã có bản hội nghị (kiểm tra khi biên tập) |

## 5. Đối chiếu với bảng công trình gốc (`docs/sota_comparison_20260811.md`)
Đã có trong tailieu.bib: TripoSR, InstantMesh, Wonder3D, Zero123++.
Chưa có: Hunyuan3D 1.0, CRM → chính là 2 entry ở mục 3.
One-2-3-45, MVDream, LGM, DreamGaussian, SyncDreamer, DUSt3R, LRM đã có sẵn.

## 6. Kết luận
- Không entry nào gây lỗi compile; không trùng lặp.
- Chỉ cần bổ sung 2 entry (Hunyuan3D, CRM) khi biên tập; không cần xóa gì.
