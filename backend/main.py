from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import UploadFile, File
from PIL import Image
import shutil
from pathlib import Path

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = BASE_DIR / "data" / "raw"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=BASE_DIR / "data"), name="data")


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

images = {
    1: [
        {
            "id": 1,
            "dataset_id": 1,
            "filename": "demo_cell_image_001.png",
            "width": 1024,
            "height": 768,
            "modality": "Microscopy",
            "status": "Imported",
        }
    ]
}

class DatasetCreate(BaseModel):
  name: str
  dataset_type: str
  description: str | None = None

class ImageCreate(BaseModel):
  filename: str
  width: int
  height: int
  modality: str | None = None

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

@app.get("/datasets/{dataset_id}/images")
def get_images(dataset_id: int):
    if dataset_id not in images:
        images[dataset_id] = []

    return images[dataset_id]


@app.post("/datasets/{dataset_id}/images")
def create_image(dataset_id: int, image: ImageCreate):
    if dataset_id not in images:
        images[dataset_id] = []

    new_image = {
        "id": len(images[dataset_id]) + 1,
        "dataset_id": dataset_id,
        "filename": image.filename,
        "width": image.width,
        "height": image.height,
        "modality": image.modality,
        "status": "Imported",
    }

    images[dataset_id].append(new_image)
    return new_image

@app.post("/datasets/{dataset_id}/upload")
async def upload_image(dataset_id: int, file: UploadFile = File(...)):
    dataset_dir = DATA_ROOT / f"dataset_{dataset_id}"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    destination = dataset_dir / file.filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with Image.open(destination) as img:
        width, height = img.size

    if dataset_id not in images:
        images[dataset_id] = []

    new_image = {
      "id": len(images[dataset_id]) + 1,
      "dataset_id": dataset_id,
      "filename": file.filename,
      "width": width,
      "height": height,
      "modality": "Unknown",
      "status": "Imported",
      "url": f"/data/raw/dataset_{dataset_id}/{file.filename}",
    }

    images[dataset_id].append(new_image)

    return new_image