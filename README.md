# Automated 3D Asset Generation from Single-View Images for Interactive Educational Games

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![PyTorch 2.5.1](https://img.shields.io/badge/PyTorch-2.5.1%2Bcu121-EE4C2C.svg)](https://pytorch.org/)
[![CUDA 12.1](https://img.shields.io/badge/CUDA-12.1-76B900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Benchmark: GSO](https://img.shields.io/badge/Benchmark-Google%20Scanned%20Objects-green.svg)](https://app.gazebosim.org/GoogleResearch/fuel/collections/Google%20Scanned%20Objects)

An end-to-end, inference-only pipeline that reconstructs interactive, watertight 3D textured assets (GLB / OBJ) from a single 2D photograph. Designed specifically for deployment on resource-constrained consumer GPUs (e.g., NVIDIA GeForce RTX 2050 with a 4 GB VRAM budget), this project bridges deep-learning 3D shape reconstruction with a lightweight client-server WebGL architecture for educational game development.

---

## Table of Contents
- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [System Requirements](#system-requirements)
- [Installation & Setup](#installation--setup)
- [Running the Web Application](#running-the-web-application)
- [Reproducing Experimental Results](#reproducing-experimental-results)
- [Experimental Benchmark Summary](#experimental-benchmark-summary)
- [Repository Structure](#repository-structure)
- [Third-Party Licenses & Acknowledgments](#third-party-licenses--acknowledgments)
- [Citation](#citation)

---

## Overview

Creating 3D digital assets for educational applications traditionally demands specialized 3D modeling expertise and time-intensive manual workflows. Recent generative 3D foundation models typically require datacenter accelerators (e.g., NVIDIA A100/A800 with 16–40 GB VRAM), precluding local execution in classroom and school computer lab settings.

This repository provides an automated, locally deployable solution featuring:
- **Single-Image Feed-Forward Reconstruction:** Integrates [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (Vision Transformer backbone + triplane NeRF decoder) to predict continuous neural radiance fields and extract explicit surface meshes via Marching Cubes in a single deterministic pass, eliminating iterative diffusion sampling delays.
- **Automated Foreground Isolation:** Leverages [rembg](https://github.com/danielgatis/rembg) (U-2-Net architecture) to segment subjects from unconstrained backgrounds, preventing background artifacts from contaminating 3D geometry.
- **Constrained-Hardware Optimization:** Operates deterministically within a **2.5 GB peak VRAM envelope** on a 4 GB GPU (NVIDIA RTX 2050), achieving a mean inference latency of **14.10 ± 3.32 s** without CUDA Out-Of-Memory (OOM) failures.
- **Interactive WebGL Toolchain:** Provides a browser-based Three.js application supporting real-time 3D inspection, spatial transforms (translate, rotate, scale), material adjustments, and direct placement into an educational 3D game sandbox.

---

## Pipeline Architecture

```text
[ Input 2D Image ] (RGB photo from commodity smartphone or dataset)
         │
         ▼
[ Background Isolation ] (rembg / U-2-Net: alpha matte extraction & foreground cropping)
         │
         ▼
[ Feed-Forward 3D Inference ] (TripoSR: ViT image encoder -> Triplane NeRF representation)
         │
         ▼
[ Isosurface Extraction & Post-Processing ] (Marching Cubes -> Open3D Poisson / Trimesh Decimation)
         │
         ▼
[ Asset Packaging ] (GLB / OBJ / PLY with embedded UV vertex colors and textures)
         │
         ▼
[ WebGL Client Interface ] (Three.js viewer -> Transform Editor -> Educational Game Sandbox)
```

---

## System Requirements

- **Operating System:** Windows 10/11 (x64) or Linux (Ubuntu 20.04/22.04 LTS)
- **Python:** 3.11 (tested on 3.11.9)
- **GPU:** NVIDIA GPU with CUDA 12.1 support (tested on NVIDIA GeForce RTX 2050 Laptop GPU, 4 GB GDDR6 VRAM; compatible with all 4 GB+ modern NVIDIA GPUs)
- **System Memory:** Minimum 8 GB RAM (16 GB recommended)
- **Disk Space:** ~5 GB for dependencies and weights (additional ~6 GB if downloading full GSO dataset)

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/pqui-345/3d-asset-generation.git
cd 3d-asset-generation
```

### 2. Create and Activate a Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install PyTorch with CUDA 12.1 Support
```bash
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

### 4. Install Dependencies
```bash
# Install core web and utility dependencies
pip install -r requirements.txt

# Install advanced scientific, geometry, and computer vision packages
pip install -r requirements-advanced.txt
```

> **Note on `tsr` package:** The `tsr/` module contains the TripoSR model implementation and is bundled directly within this repository. No external installation via PyPI is required.

### 5. Download TripoSR Model Weights
The pretrained TripoSR model checkpoint (~1.68 GB) is hosted on Hugging Face. Download `model.ckpt` and place it in `services/weights/`:

**Windows (PowerShell):**
```powershell
curl.exe -L -o services/weights/model.ckpt https://huggingface.co/stabilityai/TripoSR/resolve/main/model.ckpt
```

**Linux / macOS:**
```bash
curl -L -o services/weights/model.ckpt https://huggingface.co/stabilityai/TripoSR/resolve/main/model.ckpt
```

Verify that `services/weights/` contains:
```text
services/weights/
  ├── config.yaml
  └── model.ckpt
```

### 6. Environment Configuration
Copy the sample environment file:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
*(Optional)* Adjust `SECRET_KEY` or database settings in `.env` if desired. SQLite fallback (`3dgame.db`) is used automatically out of the box.

### 7. (Optional) Download Google Scanned Objects (GSO) Benchmark Dataset
To reproduce the template retrieval and quantitative benchmark experiments:
```bash
python scripts/download_gso.py
```

---

## Running the Web Application

Start the Flask application server:
```bash
python app.py
```

Open your browser and navigate to:
```
http://localhost:5000
```

### Application Features:
1. **Interactive 3D Generator:** Upload single or multi-angle photos, trigger background removal, and generate textured 3D models with real-time progress indicators.
2. **Asset Library:** Browse, download (GLB/OBJ), filter, and manage previously generated 3D models.
3. **WebGL 3D Transform Editor:** Inspect geometry with wireframe / texture toggles, translate, rotate, and scale assets in a 3D grid viewport.
4. **Interactive Classroom Demo:** Place generated assets directly into an interactive 3D classroom scene to test suitability for educational gameplay.

---

## Reproducing Experimental Results

All quantitative and qualitative experiments reported in the study can be reproduced using the scripts in `experiments/scripts/`:

### 1. Pilot Evaluation ($n=10$)
Evaluates baseline reconstruction feasibility, cold-start initialization latency, and peak memory:
```bash
python experiments/scripts/run_triposr_pilot.py
```

### 2. Full GSO Benchmark Evaluation ($n=30$)
Executes timed batch inference on 30 standardized objects from the Google Scanned Objects dataset:
```bash
python experiments/scripts/run_gso_experiment_30.py
```
Outputs and logs are saved to `experiments/logs/` and `experiments/outputs/`.

### 3. Quantitative Geometric Metric Evaluation
Computes rigid Iterative Closest Point (ICP) alignment, 2-way Chamfer Distance, and F-score ($\tau = 0.01$, 50,000 surface points) between predicted meshes and GSO ground-truth scans:
```bash
python experiments/scripts/run_geometry_metrics.py
```

### 4. Generate Tables, Summary Statistics, and Figures
Aggregates metric logs into descriptive statistical tables (mean ± SD) and generates comparative figures:
```bash
python experiments/scripts/make_tables_figures.py
```

---

## Experimental Benchmark Summary

Measured local performance on consumer hardware (NVIDIA GeForce RTX 2050, 4 GB VRAM) using the Google Scanned Objects (GSO) benchmark:

| Metric / Parameter | Experimental Result | Protocol / Details |
| :--- | :--- | :--- |
| **Inference Latency** | $14.10 \pm 3.32$\,s | Measured over $n=19$ timed runs; single forward pass |
| **Cold-Start Latency** | $20.43 \pm 11.69$\,s | Measured over initial pilot subset ($n=10$) |
| **Peak VRAM Consumption** | $2494$\,MB (~2.44 GB) | Monitored via `torch.cuda.max_memory_allocated()` |
| **Mesh Generation Success Rate** | 96.7% (29/30 objects) | Deterministic watertight GLB mesh production |
| **Chamfer Distance (CD)** | $0.3453 \pm 0.1301$ | Rigid ICP alignment, 50,000 surface samples ($n=29$) |
| **F-Score ($\tau = 0.01$)** | $0.0483 \pm 0.0248$ | Strict distance threshold ($10^{-2}$) ($n=29$) |
| **Multi-View Consistency** | 100% (8/8 canonical views) | Tested on convex-matte and specular-flat objects |
| **In-the-Wild Real-World Scoring**| $3.76 \pm 0.75$ / 5.00 | 51 smartphone photos, 5 dimensions, 765 evaluations |

---

## Repository Structure

```text
3d-asset-generation/
├── app.py                     # Main Flask application entry point
├── routes/                    # API route controllers and view handlers
│   ├── api_routes.py          # REST endpoints for generation, library, and downloads
│   └── main_routes.py         # Web page template routes
├── services/                  # Business logic and AI service backends
│   ├── bg_remover.py          # rembg U-2-Net background removal service
│   ├── local_tripo_service.py # Local TripoSR GPU inference manager
│   ├── mesh_generator.py      # Mesh decimation, smoothing, and format conversion
│   ├── retrieval_service.py   # FAISS-based template retrieval
│   └── weights/               # Model configuration and weights directory
│       └── config.yaml        # TripoSR architecture hyperparameters
├── tsr/                       # TripoSR core model architecture
│   ├── system.py              # TSR system module (forward pass and mesh extraction)
│   ├── models/                # ViT tokenizers, NeRF renderers, isosurface modules
│   └── utils.py               # Image preprocessing, camera math, Ray bundle creation
├── templates/                 # Jinja2 HTML templates
│   └── index.html             # Single-page web application UI
├── static/                    # Frontend client assets
│   ├── css/style.css          # UI styling (dark glassmorphism theme)
│   ├── js/app.js              # Application logic and AJAX pipeline hooks
│   └── js/asset_editor.js     # Three.js 3D viewport, gizmos, and inspector
├── experiments/               # Reproducibility suite and evaluation scripts
│   ├── scripts/               # Benchmarking, metric calculation, and chart scripts
│   ├── logs/                  # Raw execution logs and timing records
│   └── outputs/               # Generated evaluation meshes and metrics JSON
├── requirements.txt           # Core application dependencies
├── requirements-advanced.txt  # Scientific computing & evaluation dependencies
├── .env.example               # Template environment configuration
└── README.md                  # Project documentation (this file)
```

---

## Third-Party Licenses & Acknowledgments

This research pipeline builds upon open-source foundations:
- **TripoSR:** Released by VAST AI Research and Stability AI under the [MIT License](https://github.com/VAST-AI-Research/TripoSR). Pretrained weights available on Hugging Face (`stabilityai/TripoSR`).
- **rembg:** Released by Daniel Gatis under the [MIT License](https://github.com/danielgatis/rembg), utilizing the [U-2-Net](https://github.com/xuebinqin/U-2-Net) architecture.
- **Google Scanned Objects (GSO):** Curated by Google Research, licensed under [Creative Commons Attribution 4.0 International (CC-BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- **Three.js:** Released under the [MIT License](https://github.com/mrdoob/three.js).

---

