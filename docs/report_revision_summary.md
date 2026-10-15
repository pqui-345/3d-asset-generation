# Report Revision Summary

## Compilation Info
- **File**: `BaoCao_TotNghiep/main.pdf`
- **Pages**: 38
- **Size**: 1.29 MB
- **Last compiled**: 2026-07-23 14:00

## Structure
| Chapter | Title | Pages |
|---------|-------|-------|
| 1 | GIỚI THIỆU | 1-7 |
| 2 | CÁC NGHIÊN CỨU LIÊN QUAN | 8-16 |
| 3 | PHƯƠNG PHÁP ĐỀ XUẤT VÀ THIẾT KẾ THỰC NGHIỆM | 17-26 |
| 4 | KẾT QUẢ THỰC NGHIỆM | 27-35 |
| 5 | KẾT LUẬN | 36-38 |

## Key Revisions

### Chương 1
- Added 4 research questions (RQ1-RQ4)
- Clarified inference-only scope (no fine-tuning)
- Specified web demo as deliverable

### Chương 2
- Added dataset comparison table (5 datasets)
- Distinguished ShapeNet vs ShapeNetCore, Objaverse vs Objaverse-XL
- Added research results subsection (DISN, Pixel2Mesh, TripoSR published metrics)

### Chương 3
- Added GSO protocol (sampling, input, pipeline, logging, evaluation)
- Added ShapeNetCore protocol (planned, NOT executed)
- Added qualitative rubric table

### Chương 4
- Cold/warm inference separation (52.3s cold, 16.9s warm avg)
- VRAM delta calculation: 807 MB
- Median, std, min, max statistics
- Explicit "cannot compute CD/F-score" due to alignment issues
- Limitations documented

### Chương 5 (new)
- Achievement summary
- RQ1-RQ4 answers
- Limitations and future directions

## Evidence Sources
| Data | Source |
|------|--------|
| Inference times | `experiments/logs/triposr_pilot.csv` |
| Metrics summary | `experiments/logs/triposr_pilot_metrics.json` |
| GLB outputs | `experiments/outputs/predictions/triposr_pilot/` |
| GSO manifests | `experiments/data/manifests/gso_manifest.csv` |
| GSO GT meshes | `static/templates/gso/*/model.obj` |

## Pending Items
- E2: rembg comparison (needs pipeline re-run)
- E3: raw vs processed mesh comparison
- E4: multi-angle experiment
- E5: scored qualitative rubric
- Geometry metrics (blocked by alignment)
- Screenshots for H3.1, H3.4-H3.10
- Charts for time/VRAM/GLB size
- Setup guide
