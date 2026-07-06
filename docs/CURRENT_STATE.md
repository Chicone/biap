# BIAP Current State

Last updated: 2026-07-06

---

# Current milestone

## Phase 2 — Computer Vision

### Image Analysis Workspace v2 completed

BIAP has evolved from a dataset browser into a modular biomedical image analysis platform.

The Images workspace has been redesigned to support multiple image analysis modules while maintaining a clean, extensible architecture.

---

# Backend

Implemented

## Dataset management

- Generic dataset import
- Folder-based image discovery
- Dataset registration
- Thumbnail generation
- Image serving API
- Static image storage

## Vision Engine

Current modules

```
backend/
    vision/
        io.py
        preprocessing.py
        segmentation.py
        measurements.py
        visualization.py
        ground_truth.py
        metrics.py
```

Implemented functionality

- Otsu threshold segmentation
- Connected component analysis
- Region measurements
- Prediction overlay generation
- Ground-truth overlay generation
- Ground-truth mask merging
- Segmentation evaluation

Evaluation metrics

- IoU
- Dice coefficient
- Precision
- Recall

---

# Frontend

Implemented

## Dataset Workspace

- Dataset management
- Dataset import
- Image browsing
- Dataset preview

## Image Analysis Workspace

Current architecture

```
ImagesTab
│
├── ImageViewer
├── AnalysisSelector
├── SegmentationPanel
├── SegmentationResults
└── ImageBrowser
```

Implemented functionality

- Full-resolution image preview
- Scrollable thumbnail browser
- Prediction overlays
- Ground-truth overlays
- Bright / Dark foreground selection
- Automatic segmentation evaluation
- Modular analysis architecture

---

# Supported datasets

✓ Generic image folders

✓ BBBC038 (Data Science Bowl)

Current testing dataset

BBBC038

---

# Current capabilities

The platform can

- Import biomedical datasets
- Browse microscopy images
- Display prediction overlays
- Display ground-truth overlays
- Run Otsu segmentation
- Detect connected objects
- Measure segmented regions
- Compare prediction against ground truth
- Compute IoU, Dice, Precision and Recall
- Support future image-analysis modules through a modular frontend architecture

---

# Current Image Analysis Architecture

```
Image Preview

↓

Analysis Selector

↓

Selected Analysis Module

↓

Results

↓

Scrollable Image Browser
```

Currently implemented analysis

- Segmentation

Future analysis modules

- Morphology
- Texture
- Intensity
- Feature Extraction
- Classical Machine Learning
- Deep Learning
- Graph-based Analysis

---

# Immediate objective

Continue expanding the modular Image Analysis Workspace.

Next planned module

Morphology

Possible morphology measurements

- Area
- Perimeter
- Circularity
- Solidity
- Eccentricity
- Bounding box
- Centroid

---

# Long-term pipeline

Image

↓

Preprocessing

↓

Segmentation

↓

Morphological Analysis

↓

Feature Extraction

↓

Machine Learning

↓

Deep Learning

↓

Graph Neural Networks

↓

Large Language Models

↓

Agentic AI

---

# Technical debt

- Refactor SegmentationPanel and SegmentationResults into a single SegmentationModule
- Improve loading indicators
- Dataset metadata viewer
- Dataset deletion
- Dataset search and filtering
- Thumbnail caching
- Background task execution

---

# Notes

The Images workspace is now designed around independent analysis modules.

Segmentation is the first implemented module.

Future image-analysis functionality should be implemented as additional modules without modifying the overall Images workspace architecture.