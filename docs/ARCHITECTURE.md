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
 Manager     Engine         (future)       (future)
        │
        ▼
 Experiment Manager
        │
        ▼
 Results / Models / Reports
```

The frontend communicates exclusively through REST APIs.

Each backend module is responsible for a single domain and can evolve independently.

---

# Frontend Architecture

```text
ImagesTab
│
├── ImageViewer
│
├── AnalysisSelector
│
├── Segmentation
│      ├── SegmentationPanel
│      └── SegmentationResults
│
├── Morphology
│      ├── MorphologyPanel
│      └── MorphologyResults
│
├── Intensity
│      ├── IntensityPanel
│      └── IntensityResults
│
└── ImageBrowser
```

Only the selected analysis module is rendered.

Future modules

- Texture
- Feature Extraction
- Machine Learning
- Deep Learning

---

# Backend Architecture

```text
backend/
│
├── api/
├── datasets/
├── models/
│
└── vision/
      ├── io.py
      ├── preprocessing.py
      ├── segmentation.py
      ├── measurements.py
      ├── visualization.py
      ├── ground_truth.py
      └── metrics.py
```

The Vision Engine is intentionally modular.

Segmentation produces labelled objects.

Object-analysis modules (Morphology, Intensity, Texture, etc.) operate on those segmented objects.

---

# Design Principles

- Modular architecture
- Separation of concerns
- Experiment-driven workflows
- Reusable analysis modules
- Extensible AI pipeline
- REST-based frontend/backend communication

---

# Long-term Vision

The architecture is intentionally designed to evolve from classical image analysis toward:

- Machine Learning
- Deep Learning
- Graph Neural Networks
- Large Language Models
- Agentic AI

without requiring architectural redesign.