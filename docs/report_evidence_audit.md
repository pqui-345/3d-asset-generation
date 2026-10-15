# Report Evidence Audit

## Figures Audit

| Figure | Path | Exists | Notes |
|--------|------|--------|-------|
| logo_ctu.png | `BaoCao_TotNghiep/report_images/logo_ctu.png` | Yes | Trường ĐH Cần Thơ logo |
| h3_2_anh_goc_mau.png | `BaoCao_TotNghiep/report_images/h3_2_anh_goc_mau.png` | Yes | Ảnh gốc case study |
| h3_3_anh_tach_nen.png | `BaoCao_TotNghiep/report_images/h3_3_anh_tach_nen.png` | Yes | Ảnh sau rembg |
| visual_comparisons.jpg | `BaoCao_TotNghiep/report_images/visual_comparisons.jpg` | Yes | So sánh mesh |
| h3_1_pipeline_he_thong.png | `BaoCao_TotNghiep/report_images/` | **MISSING** | Sơ đồ pipeline - cần vẽ |
| h3_4_giao_dien_tai_anh.png | Not checked | **MISSING** | Screenshot upload |
| h3_5_trang_thai_suy_luan.png | Not checked | **MISSING** | Screenshot processing |
| h3_6_viewer_ket_qua.png | Not checked | **MISSING** | Screenshot viewer |
| h3_7_goc_nhin_asset.png | Not checked | **MISSING** | Multi-angle composite |
| h3_8_asset_editor.png | Not checked | **MISSING** | Screenshot editor |
| h3_9_truoc_sau_chinh_sua.png | Not checked | **MISSING** | Before/after edit |
| h3_10_xuat_tep_asset.png | Not checked | **MISSING** | Screenshot export |

## Tables Audit

| Table | Label | Data Source | Verified |
|-------|-------|-------------|----------|
| Các thành phần trong quy trình | tab:components | Conceptual | N/A |
| Vai trò dataset | tab:dataset-role | Conceptual | N/A |
| Phạm vi chức năng web demo | tab:web-scope | Conceptual | N/A |
| Kịch bản thực nghiệm | tab:scenarios | Conceptual | N/A |
| Khung đánh giá định tính | tab:qualitative-rubric | Conceptual | N/A |
| Môi trường triển khai | tab:environment | Actual machine | Verified (R2050, i5-12450HX, Win11) |
| Kết quả suy luận pilot | tab:pilot-results | triposr_pilot.csv | Verified |
| Danh sách hình | (caption*) | N/A | Checklist only |

## Metrics Audit

| Metric | Value | Source | Verification |
|--------|-------|--------|-------------|
| n_attempt | 10 | triposr_pilot.csv | CSV has 10 samples |
| n_success | 10 | triposr_pilot.csv | All 10 completed |
| R_success | 100% | Calculated | 10/10 |
| avg_inference_time | 20.4 s | triposr_pilot_metrics.json | Includes cold start (52.3s first sample) |
| warm_avg_time | 16.9 s | Calculated | Excluding first cold-start sample |
| std_inference_time | 11.1 s | triposr_pilot_metrics.json | High due to cold-start outlier |
| median_inference_time | 17.35 s | Calculated | More representative |
| avg_vram_peak | 2494 MB | triposr_pilot_metrics.json | Verified |
| avg_vram_before | 1687 MB | CSV column vram_before_mb | Verified |
| delta_vram | 807 MB | Calculated | 2494 - 1687 |
| avg_vertices | 103121 | triposr_pilot_metrics.json | Consistent with CSV |
| avg_faces | 206063 | triposr_pilot_metrics.json | Consistent with CSV |
| avg_glb_size | 3.84 MB | triposr_pilot_metrics.json | Consistent with CSV |
| Chamfer Distance | N/A | N/A | Not computed (no aligned GT) |
| F-score | N/A | N/A | Not computed |
| Precision/Recall | N/A | N/A | Not computed |
