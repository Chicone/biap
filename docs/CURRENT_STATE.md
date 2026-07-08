# BIAP Current State

Last updated: 2026-07-07

---

# Current milestone

## Phase 2 — Computer Vision

### Image Analysis Workspace v2 completed

BIAP has evolved from a dataset browser into a modular biomedical image analysis platform.

The Images workspace now supports multiple independent image analysis modules built on a common architecture.

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

```text
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
- Bright/Dark foreground selection
- Connected component analysis
- Morphological measurements
- Intensity measurements
- Prediction overlay generation
- Ground-truth overlay generation
- Selected-object overlay
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

```text
ImagesTab
│
├── ImageViewer
├── AnalysisSelector
├── Segmentation
│     ├── SegmentationPanel
│     └── SegmentationResults
├── Morphology
│     ├── MorphologyPanel
│     └── MorphologyResults
├── Intensity
│     ├── IntensityPanel
│     └── IntensityResults
└── ImageBrowser
```

Implemented functionality

- Full-resolution image preview
- Scrollable thumbnail browser
- Prediction overlays
- Ground-truth overlays
- Bright/Dark foreground selection
- Automatic segmentation evaluation
- Interactive object selection
- Object highlighting on the original image
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
- Perform morphology analysis
- Perform intensity analysis
- Highlight selected objects
- Compare prediction against ground truth
- Compute IoU, Dice, Precision and Recall

---

# Current Image Analysis Architecture

```text
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
- Morphology
- Intensity

Future analysis modules

- Texture
- Feature Extraction
- Classical Machine Learning
- Deep Learning
- Graph-based Analysis

---

# Morphology measurements

- Area
- Perimeter
- Circularity
- Solidity
- Eccentricity
- Major axis
- Minor axis
- Equivalent diameter
- Convex area
- Orientation
- Bounding box
- Centroid

---

# Intensity measurements

- Mean intensity
- Median intensity
- Minimum intensity
- Maximum intensity
- Standard deviation
- Integrated intensity

---

# Immediate objective

Continue expanding the Vision Engine.

Next planned module

Texture Analysis

---

# Long-term pipeline

Image

↓

Preprocessing

↓

Segmentation

↓

Morphology

↓

Intensity

↓

Texture

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

- Refactor common analysis table components
- Generic object-selection infrastructure
- Improve loading indicators
- Dataset metadata viewer
- Dataset deletion
- Dataset search and filtering
- Thumbnail caching
- Background task execution

---

# Notes

The Vision Engine currently contains three analysis modules:

- Segmentation
- Morphology
- Intensity

Future analysis modules should follow the same modular architecture.