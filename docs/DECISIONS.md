## 2026-07-09

### Feature Analysis Workspace

Feature Engineering has evolved into a broader Feature Analysis workspace.

The workspace now includes:

- Feature construction
- Feature filtering
- Feature transformation
- Dimensionality reduction
- Projection visualization
- Feature matrix exploration

This architecture leaves room for future additions such as feature statistics, clustering and feature importance.

---

### Projection Viewer

Instead of separate PCA and UMAP viewers, BIAP now provides a generic Projection Viewer.

Current projections

- PCA
- UMAP

Future projections

- t-SNE

Projection visualisation is independent from the underlying dimensionality reduction algorithm.

---

### Dataset Importers

Dataset import has been redesigned around importer plugins.

Each public dataset will implement its own importer.

Current importers

- Generic
- BBBC021

Future importers

- BBBC038
- MoNuSeg
- PanNuke
- Cell Painting