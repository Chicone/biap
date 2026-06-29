# BIAP Architecture

BIAP follows a modular client-server architecture.

```
Frontend (React)
        │
        ▼
FastAPI Backend
        │
 ┌──────┼────────┬────────┬────────┬─────────┐
 │      │        │        │        │
Dataset Vision Analysis  GNN      LLM
Manager Engine  Engine   Engine   Engine
        │
        ▼
 Experiment Manager
        │
        ▼
 Stored Results / Models / Reports
```

The frontend communicates exclusively through REST APIs.

Each backend module is responsible for a single domain and can evolve independently.

The architecture is intentionally designed to accommodate future AI agents capable of orchestrating complete experimental workflows.