# BIAP Current State

Last updated: 2026-07-09

---

# Current milestone

## Phase 3 — Feature Analysis

Completed

### Vision Engine

Implemented

- Segmentation
- Morphology
- Intensity
- Texture

---

### Feature Analysis

Implemented

- Feature set builder
- Feature source selection
- Constant feature removal
- Correlation filtering
- Standard scaling
- Min-Max scaling
- Robust scaling
- PCA
- UMAP
- Feature matrix viewer
- Plotly projection viewer
- Dynamic "Color by Feature"

---

### Projection Viewer

Implemented

- PCA projection
- UMAP projection
- Interactive Plotly scatter plot
- Dynamic feature colouring
- Hover metadata

---

### Dataset Import

Implemented

- Generic folder importer
- BBBC038 importer
- Initial BBBC021 metadata importer

Current BBBC021 support

- Metadata loading
- Compound table
- Mechanism-of-action table
- Metadata merging

Importer architecture is now plugin-based.

---

### Current pipeline

```text
Images

↓

Segmentation

↓

Morphology

↓

Intensity

↓

Texture

↓

Feature Analysis

↓

Projection Viewer

↓

Machine Learning (next)
```

---

# Immediate objective

Implement complete BBBC021 import.

This includes

- Three-channel microscopy import
- Metadata import
- Compound information
- Mechanism of action labels
- Multi-channel image representation

The first machine-learning benchmark will use BBBC021.