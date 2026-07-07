from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import UploadFile, File
from PIL import Image
import shutil
from pathlib import Path

from vision.segmentation import segment_otsu
from vision.io import load_image, pil_to_numpy
from vision.preprocessing import to_grayscale
from vision.segmentation import threshold, connected_components
from vision.measurements import measure_regions, summarize_regions
from db import init_db, get_connection
from io import BytesIO
from fastapi.responses import StreamingResponse
from PIL import Image
import numpy as np

from vision.visualization import overlay_mask, overlay_selected_label
from vision.ground_truth import merge_instance_masks
from vision.metrics import iou, dice_coefficient, precision, recall


app = FastAPI()
init_db()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = BASE_DIR / "data" / "raw"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=BASE_DIR / "data"), name="data")
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

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

class DatasetCreate(BaseModel):
  name: str
  dataset_type: str
  description: str | None = None

class ImageCreate(BaseModel):
  filename: str
  width: int
  height: int
  modality: str | None = None

class FolderImportRequest(BaseModel):
  folder_path: str
  max_images: int = 20

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

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM datasets
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]

@app.post("/experiments/{experiment_id}/datasets")
def create_dataset(experiment_id: int, dataset: DatasetCreate):

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO datasets
            (name, dataset_type, description)
            VALUES (?, ?, ?)
            """,
            (
                dataset.name,
                dataset.dataset_type,
                dataset.description,
            ),
        )

        dataset_id = cursor.lastrowid

    return {
        "id": dataset_id,
        "experiment_id": experiment_id,
        "name": dataset.name,
        "dataset_type": dataset.dataset_type,
        "description": dataset.description,
        "image_count": 0,
        "status": "Imported",
    }


@app.get("/datasets/{dataset_id}/images")
def get_images(dataset_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ?
            ORDER BY id
            """,
            (dataset_id,),
        ).fetchall()

    return [dict(row) for row in rows]

@app.get("/datasets/{dataset_id}/images/{image_id}/grayscale")
def get_grayscale_info(dataset_id: int, image_id: int):
    if dataset_id not in images:
        raise HTTPException(status_code=404, detail="Dataset not found")

    image_record = next(
        (img for img in images[dataset_id] if img["id"] == image_id),
        None,
    )

    if image_record is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_path = DATA_ROOT / f"dataset_{dataset_id}" / image_record["filename"]

    image = load_image(image_path)
    image_array = pil_to_numpy(image)
    gray = to_grayscale(image_array)

    return {
        "filename": image_record["filename"],
        "original_shape": image_array.shape,
        "grayscale_shape": gray.shape,
        "dtype": str(gray.dtype),
    }


@app.post("/datasets/{dataset_id}/images")
def create_image(dataset_id: int, image: ImageCreate):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images
            (dataset_id, filename, width, height, modality, status, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                image.filename,
                image.width,
                image.height,
                image.modality,
                "Imported",
                None,
            ),
        )

        image_id = cursor.lastrowid

    return {
        "id": image_id,
        "dataset_id": dataset_id,
        "filename": image.filename,
        "width": image.width,
        "height": image.height,
        "modality": image.modality,
        "status": "Imported",
        "url": None,
    }

@app.post("/datasets/{dataset_id}/upload")
async def upload_image(dataset_id: int, file: UploadFile = File(...)):
    dataset_dir = DATA_ROOT / f"dataset_{dataset_id}"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    destination = dataset_dir / file.filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with Image.open(destination) as img:
        width, height = img.size

    url = f"/data/raw/dataset_{dataset_id}/{file.filename}"

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images
            (dataset_id, filename, width, height, modality, status, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                file.filename,
                width,
                height,
                "Unknown",
                "Imported",
                url,
            ),
        )

        image_id = cursor.lastrowid

    return {
        "id": image_id,
        "dataset_id": dataset_id,
        "filename": file.filename,
        "width": width,
        "height": height,
        "modality": "Unknown",
        "status": "Imported",
        "url": url,
    }

@app.post("/datasets/{dataset_id}/import-folder")
async def import_folder(dataset_id: int, request: FolderImportRequest):
    source_folder = Path(request.folder_path)

    if not source_folder.exists():
        return {"error": "Folder not found"}

    dataset_dir = DATA_ROOT / f"dataset_{dataset_id}"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    imported = 0
    MAX_FOLDER_IMPORT = request.max_images

    with get_connection() as conn:
        for image_file in source_folder.rglob("images/*"):
            if imported >= MAX_FOLDER_IMPORT:
                break

            if image_file.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue

            sample_dir = image_file.parent.parent
            sample_id = sample_dir.name

            destination_sample_dir = dataset_dir / sample_id
            destination_images_dir = destination_sample_dir / "images"
            destination_masks_dir = destination_sample_dir / "masks"

            destination_images_dir.mkdir(parents=True, exist_ok=True)

            destination_image = destination_images_dir / image_file.name
            shutil.copy2(image_file, destination_image)

            source_masks_dir = sample_dir / "masks"
            ground_truth_dir = None

            if source_masks_dir.exists():
                shutil.copytree(
                    source_masks_dir,
                    destination_masks_dir,
                    dirs_exist_ok=True,
                )
                ground_truth_dir = f"dataset_{dataset_id}/{sample_id}/masks"

            with Image.open(destination_image) as img:
                width, height = img.size

            relative_image_path = f"dataset_{dataset_id}/{sample_id}/images/{image_file.name}"
            url = f"/data/raw/{relative_image_path}"

            conn.execute(
                """
                INSERT INTO images
                (dataset_id, filename, width, height, modality, status, url, ground_truth_dir)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    relative_image_path,
                    width,
                    height,
                    "Unknown",
                    "Imported",
                    url,
                    ground_truth_dir,
                ),
            )

            imported += 1

    return {
        "imported": imported,
        "total_images": len(get_images(dataset_id)),
    }

@app.get("/datasets/{dataset_id}/images/{image_id}/analysis")
def analyze_image(dataset_id: int, image_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ? AND id = ?
            """,
            (dataset_id, image_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_record = dict(row)
    image_path = DATA_ROOT / image_record["filename"]
    image = load_image(image_path)
    image_array = pil_to_numpy(image)
    gray = to_grayscale(image_array)

    binary, otsu_value = segment_otsu(
      gray,
      foreground="bright",
      return_threshold=True,
    )

    labels = connected_components(binary)
    regions = measure_regions(labels)
    summary = summarize_regions(regions)

    return {
      "dataset_id": dataset_id,
      "image_id": image_id,
      "filename": image_record["filename"],
      "threshold": otsu_value,
      "num_objects": len(regions),
      "summary": summary,
      "objects": regions,
    }

@app.get("/datasets/{dataset_id}/images/{image_id}/overlay")
def get_image_overlay(
    dataset_id: int,
    image_id: int,
    foreground: str = "bright",
):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ? AND id = ?
            """,
            (dataset_id, image_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_record = dict(row)
    image_path = DATA_ROOT / image_record["filename"]
    image = load_image(image_path)
    image_array = pil_to_numpy(image)

    gray = to_grayscale(image_array)
    binary, threshold = segment_otsu(
      gray,
      foreground=foreground,
      return_threshold=True,
    )

    if image_array.ndim == 2:
        rgb_image = np.stack([image_array] * 3, axis=-1)
    else:
        rgb_image = image_array[:, :, :3]

    overlay = overlay_mask(
        rgb_image,
        binary,
        color=(255, 0, 0),
        alpha=0.4,
    )

    output = BytesIO()
    Image.fromarray(overlay).save(output, format="PNG")
    output.seek(0)

    return StreamingResponse(output, media_type="image/png")

@app.get("/datasets/{dataset_id}/images/{image_id}/objects/{object_label}/overlay")
def get_selected_object_overlay(
    dataset_id: int,
    image_id: int,
    object_label: int,
    foreground: str = "bright",
):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ? AND id = ?
            """,
            (dataset_id, image_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_record = dict(row)
    image_path = DATA_ROOT / image_record["filename"]
    image = load_image(image_path)
    image_array = pil_to_numpy(image)

    gray = to_grayscale(image_array)
    binary, _ = segment_otsu(
        gray,
        foreground=foreground,
        return_threshold=True,
    )

    labels = connected_components(binary)

    if not np.any(labels == object_label):
        raise HTTPException(
            status_code=404,
            detail="Object label not found",
        )

    if image_array.ndim == 2:
        rgb_image = np.stack([image_array] * 3, axis=-1)
    else:
        rgb_image = image_array[:, :, :3]

    overlay = overlay_selected_label(
        rgb_image,
        labels,
        selected_label=object_label,
    )

    output = BytesIO()
    Image.fromarray(overlay).save(output, format="PNG")
    output.seek(0)

    return StreamingResponse(output, media_type="image/png")

@app.get("/datasets/{dataset_id}/images/{image_id}/ground-truth-overlay")
def get_ground_truth_overlay(dataset_id: int, image_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ? AND id = ?
            """,
            (dataset_id, image_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_record = dict(row)

    if not image_record.get("ground_truth_dir"):
        raise HTTPException(
            status_code=404,
            detail="Ground truth not available for this image",
        )

    image_path = DATA_ROOT / image_record["filename"]
    mask_dir = DATA_ROOT / image_record["ground_truth_dir"]

    image = load_image(image_path)
    image_array = pil_to_numpy(image)

    if image_array.ndim == 2:
        rgb_image = np.stack([image_array] * 3, axis=-1)
    else:
        rgb_image = image_array[:, :, :3]

    merged_mask = merge_instance_masks(mask_dir)

    overlay = overlay_mask(
        rgb_image,
        merged_mask,
        color=(0, 255, 0),
        alpha=0.4,
    )

    output = BytesIO()
    Image.fromarray(overlay).save(output, format="PNG")
    output.seek(0)

    return StreamingResponse(output, media_type="image/png")

@app.get("/datasets/{dataset_id}/images/{image_id}/evaluate")
def evaluate_image(
    dataset_id: int,
    image_id: int,
    foreground: str = "bright",
):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ? AND id = ?
            """,
            (dataset_id, image_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_record = dict(row)

    if not image_record.get("ground_truth_dir"):
        raise HTTPException(
            status_code=404,
            detail="Ground truth not available for this image",
        )

    image_path = DATA_ROOT / image_record["filename"]
    mask_dir = DATA_ROOT / image_record["ground_truth_dir"]

    image = load_image(image_path)
    image_array = pil_to_numpy(image)
    gray = to_grayscale(image_array)

    prediction, otsu_value = segment_otsu(
        gray,
        foreground=foreground,
        return_threshold=True,
    )

    ground_truth = merge_instance_masks(mask_dir)

    return {
        "dataset_id": dataset_id,
        "image_id": image_id,
        "filename": image_record["filename"],
        "method": "otsu",
        "foreground": foreground,
        "threshold": otsu_value,
        "iou": iou(prediction, ground_truth),
        "dice": dice_coefficient(prediction, ground_truth),
        "precision": precision(prediction, ground_truth),
        "recall": recall(prediction, ground_truth),
    }