# Bảng công trình gốc (SOTA baselines) — tham khảo cho luận văn

Ngày: 2026-08-11 | Run tham chiếu: `ablation_full_20260811` | Tác giả: Tran Phu Qui (B2303775)

Mục đích: bảng tổng hợp các công trình liên quan để viết phần "tổng quan công trình gốc"
và đối chiếu tham khảo với kết quả thí nghiệm ablation của đề tài. Mọi con số lấy từ ấn
bản chính thức (arXiv / kỷ yếu hội nghị) — không trích dẫn thứ cấp.

## 1. Bảng tổng hợp phương pháp

| Phương pháp | Nguồn chính thức | Loại mô hình | Đầu ra | Thời gian inference | Metric công bố | Ghi chú so sánh với đề tài |
|---|---|---|---|---|---|---|
| **TripoSR** (Tochilkin et al., 2024) | arXiv:2403.02151 (Stability AI + Tripo AI), MIT | Transformer feed-forward, LRM-based, triplane-NeRF → mesh (Marching Cubes) | Mesh có texture | ~0.5 s trên A100 | GSO val (≈300 vật thể, lọc thủ công): CD **0.111**, FS@0.1 **0.651**, FS@0.2 0.871, FS@0.5 0.980 (10K điểm, brute-force xoay + ICP) | Là backbone của đề tài; độ đo cùng họ (CD/F-score) nhưng khác protocol → KHÔNG so sánh trực tiếp số |
| **InstantMesh** (Xu et al., 2024) | arXiv:2404.07191, ECCV 2024 | Sparse-view diffusion + LRM (transformer), Flexicubes | Mesh texture UV | ~10 s trên A100 | Đánh giá trên GSO + Objaverse riêng protocol | Đại diện nhóm LRM sau TripoSR |
| **Wonder3D** (Long et al., 2023) | arXiv:2310.15008 | Cross-domain diffusion (normal + color), NeRF/mesh sau distillation | Mesh | Vài phút (per-shape optimization) | Đánh giá riêng protocol | Đại diện nhóm optimization-based |
| **Zero123++** (Shi et al., 2023) | arXiv:2310.15110 | Multi-view diffusion base model | Multi-view image | — | Dùng làm sinh đa góc nhìn | Không ra mesh trực tiếp |
| **CRM** (Wang et al., 2024) | arXiv:2403.05034, ECCV 2024 | Convolutional U-Net, Flexicubes, 6 orthographic views + CCM | Mesh texture UV | ~10 s trên A800 | Đánh giá riêng protocol (geometry + texture PSNR/SSIM/LPIPS) | Đại diện nhóm CNN feed-forward |
| **Hunyuan3D 1.0** (Yang et al., 2024) | arXiv:2411.02293 (Tencent) | Multi-view diffusion (≈4 s) + sparse-view LRM (≈7 s); lite/standard | Mesh | Lite ≈10 s, standard ≈25 s (chưa gồm UV unwrap ≈15 s) | So sánh CD/F-score với nhiều baseline trong báo cáo kỹ thuật | Đại diện thế hệ 2024–2025, chất lượng cao hơn TripoSR theo báo cáo gốc |

## 2. Số liệu chính thức đã xác minh (TripoSR, Bảng 2 của báo cáo kỹ thuật — GSO validation)

| Phương pháp | CD ↓ | FS@0.1 ↑ | FS@0.2 ↑ | FS@0.5 ↑ |
|---|---|---|---|---|
| One-2-3-45 | 0.227 | 0.382 | 0.630 | 0.878 |
| ZeroShape | 0.160 | 0.489 | 0.757 | 0.952 |
| TGS | 0.122 | 0.637 | 0.846 | 0.968 |
| OpenLRM | 0.180 | 0.430 | 0.698 | 0.938 |
| **TripoSR** | **0.111** | **0.651** | **0.871** | **0.980** |

Ghi chú protocol của báo cáo gốc: ~300 vật thể GSO (đã lọc), lấy isosurface bằng Marching
Cubes, mẫu 10K điểm, căn chỉnh bằng brute-force xoay + ICP.

## 3. Kết quả của đề tài (chỉ để tham chiếu nội bộ — KHÔNG đặt cạnh bảng 2 vì khác protocol)

Run `ablation_full_20260811`, baseline `standard` (512px, rembg, bounding-box crop, padding 0.85),
28 vật thể GSO (đã loại 1 ca trục mơ hồ), chuẩn hóa bbox=1, tự chọn trục z-up theo silhouette,
tìm xoay quanh trục z + ICP (metric `*_post_align`):

| Setting | cd_post_align ↓ | f_tau0.1_post_align ↑ | f_tau0.2_post_align ↑ | f_tau0.5_post_align ↑ |
|---|---|---|---|---|
| standard (n=28) | 0.0600 (median 0.0535) | 0.796 | 0.965 | 1.000 |

Lý do không so trực tiếp với bảng 2: (i) tập con vật thể khác (28 vs ≈300), (ii) đơn vị CD
chuẩn hóa bbox=1 khác thang đo gốc của báo cáo, (iii) quy trình căn chỉnh khác
(axis z-up theo silhouette IoU + rotation search trên z + ICP), (iv) rembg + crop riêng.

## 4. Nguồn chính thức đã kiểm chứng

- TripoSR: https://arxiv.org/abs/2403.02151 (bảng 2, mục 3)
- InstantMesh: https://arxiv.org/abs/2404.07191
- Wonder3D: https://arxiv.org/abs/2310.15008
- Zero123++: https://arxiv.org/abs/2310.15110
- CRM: https://arxiv.org/abs/2403.05034 (inference ~10 s A800)
- Hunyuan3D 1.0: https://arxiv.org/abs/2411.02293 (lite ~10 s, standard ~25 s; multi-view ≈4 s + reconstruction ≈7 s; UV unwrap ≈15 s không gồm trong thời gian trên)
