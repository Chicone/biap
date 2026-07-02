from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExperimentCreate(BaseModel):
  name: str
  domain: str
  description: str | None = None

experiments = [
    {
        "id": 1,
        "name": "Cell morphology pilot",
        "domain": "Microscopy",
        "status": "Running",
        "updated": "Today",
    },
    {
        "id": 2,
        "name": "Tumour segmentation",
        "domain": "Histology",
        "status": "Ready",
        "updated": "Yesterday",
    },
]

datasets = {
    1: [
        {
            "id": 1,
            "experiment_id": 1,
            "name": "Pilot microscopy dataset",
            "dataset_type": "Microscopy",
            "description": "Initial demo dataset for the cell morphology experiment",
            "image_count": 0,
            "status": "Imported",
        }
    ],
    2: [],
}

class DatasetCreate(BaseModel):
  name: str
  dataset_type: str
  description: str | None = None

@app.get("/experiments")
def get_experiments():
    return experiments

@app.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: int):
    for experiment in experiments:
        if experiment["id"] == experiment_id:
            return experiment

    raise HTTPException(status_code=404, detail="Experiment not found")

@app.post("/experiments")
def create_experiment(experiment: ExperimentCreate):
    new_experiment = {
        "id": len(experiments) + 1,
        "name": experiment.name,
        "domain": experiment.domain,
        "description": experiment.description,
        "status": "Draft",
        "updated": "Just now",
    }

    experiments.append(new_experiment)
    return new_experiment

@app.get("/experiments")
def get_experiments():
    return [
        {
            "id": 1,
            "name": "Cell morphology pilot",
            "domain": "Microscopy",
            "status": "Running",
            "updated": "Today",
        },
        {
            "id": 2,
            "name": "Tumour segmentation",
            "domain": "Histology",
            "status": "Ready",
            "updated": "Yesterday",
        },
    ]

@app.get("/experiments/{experiment_id}/datasets")
def get_datasets(experiment_id: int):
    if experiment_id not in datasets:
        datasets[experiment_id] = []

    return datasets[experiment_id]


@app.post("/experiments/{experiment_id}/datasets")
def create_dataset(experiment_id: int, dataset: DatasetCreate):
    if experiment_id not in datasets:
        datasets[experiment_id] = []

    new_dataset = {
        "id": len(datasets[experiment_id]) + 1,
        "experiment_id": experiment_id,
        "name": dataset.name,
        "dataset_type": dataset.dataset_type,
        "description": dataset.description,
        "image_count": 0,
        "status": "Imported",
    }

    datasets[experiment_id].append(new_dataset)
    return new_dataset