# BIAP Architecture

## Overview

BIAP follows a modular client-server architecture designed for extensible biomedical image analysis and AI-assisted scientific workflows.

```text
React Frontend
        │
        ▼
FastAPI Backend
        │
 ┌─────────────┬──────────────┬──────────────┬──────────────┐
 │             │              │              │
 Dataset     Vision         ML Engine      AI Engine
 Manager     Engine         (in progress)  (future)
        │
        ▼
 Experiment Manager
        │
        ▼
 Results / Models / Reports
```

The frontend communicates exclusively through REST APIs.

---

# Frontend Architecture

```text
Dataset Workspace
│
├── Images
├── Feature Analysis
│      ├── Feature Set Builder
│      ├── Projection Viewer
│      ├── Feature Matrix
│      └── Feature Set Summary
│
└── (Machine Learning - planned)
```

Feature Analysis currently includes:

- Feature source selection
- Feature filtering
- Feature transformation
- PCA
- UMAP
- Interactive Plotly projection viewer
- Feature matrix explorer

---

# Backend Architecture

```text
backend/
│
├── api/
├── dataset_importers/
│      ├── generic.py
│      └── bbbc021.py
│
├── models/
│
└── vision/
       io.py
       preprocessing.py
       segmentation.py
       measurements.py
       visualization.py
       ground_truth.py
       metrics.py
```

The importer architecture is dataset-specific.

Each supported public dataset will eventually have its own importer implementing a common interface.

---

# Vision Pipeline

```text
Image

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

Machine Learning

↓

Deep Learning
```

---

# Design Principles

- Modular architecture
- Dataset-specific importers
- Separation of concerns
- Experiment-driven workflows
- Reusable analysis modules
- Interactive scientific visualization
- REST-based frontend/backend communication