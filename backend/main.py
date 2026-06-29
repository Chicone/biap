from fastapi import FastAPI
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

@app.get("/experiments")
def get_experiments():
    return experiments

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