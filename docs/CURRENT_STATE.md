# BIAP Current State

Last updated: 2026-07-03

---

# Current milestone

Phase 2 — Computer Vision

The platform has completed the transition from the old Experiment Workspace to the new Dataset Workspace.

The next development stage focuses on biomedical image analysis using BBBC038.

---

# Backend

Implemented

- Generic dataset import
- Folder-based image discovery
- Dataset registration
- Thumbnail generation
- Image serving API
- Preview API
- Static image storage

Current backend modules

backend/
    api/
    datasets/
    models/
    utils/

---

# Frontend

Implemented

- Dataset Workspace
- Dataset cards
- Image gallery
- Thumbnail grid
- Image preview dialog
- Dataset import dialog

---

# Supported datasets

✓ Generic image folders

✓ BBBC038

Current testing dataset:
BBBC038

---

# Current capabilities

The platform can

- Import biomedical datasets
- Display thumbnails
- Open full-resolution images
- Navigate datasets
- Store datasets independently of experiments

---

# Immediate objective

Begin Vision Engine development.

Create

vision/
    preprocessing.py
    segmentation.py
    measurements.py
    mask_utils.py

---

# Next feature

Display BBBC038 segmentation masks as overlays.

---

# Future pipeline

Image
↓

Preprocessing

↓

Segmentation

↓

Feature Extraction

↓

Machine Learning

↓

Deep Learning

↓

Graph Neural Networks

↓

LLM Interpretation

---

# Technical debt

- Improve thumbnail caching
- Better loading indicators
- Metadata viewer
- Dataset deletion
- Dataset search/filter

---

# Notes

The previous Experiment Workspace has been fully retired.

Datasets are now the central object of Phase 2.

Future AI modules will consume datasets produced by the Dataset Workspace.