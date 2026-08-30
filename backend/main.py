from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import UploadFile, File
from PIL import Image
import shutil
from pathlib import Path
import json

from vision.segmentation import segment_otsu
from vision.io import load_image, pil_to_numpy, normalize_for_display
from vision.preprocessing import to_grayscale
from vision.segmentation import threshold, connected_components
from vision.measurements import (
    measure_regions,
    summarize_regions,
    measure_intensity,
    summarize_intensity,
    measure_texture,
    summarize_texture,
)
from db import init_db, get_connection
from io import BytesIO
from fastapi.responses import StreamingResponse
from PIL import Image
import numpy as np

from vision.visualization import overlay_mask, overlay_selected_label
from vision.ground_truth import merge_instance_masks
from vision.metrics import iou, dice_coefficient, precision, recall
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
import umap
from dataset_importers.bbbc021 import BBBC021Importer
from dataset_importers.jump import JUMPImporter
from ml.trainer import train_model, get_available_targets
from vision.foundation_models.dinov2 import get_dinov2_model

app = FastAPI()
init_db()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = BASE_DIR / "data" / "raw"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=BASE_DIR / "data"), name="data")
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def resolve_image_path(image_record, image_id: int, channel: str | None = None):
  if channel is None:
    return DATA_ROOT / image_record["filename"]

  with get_connection() as conn:
    channel_row = conn.execute(
      """
      SELECT *
      FROM image_channels
      WHERE image_id = ?
      AND LOWER(channel_name) = LOWER(?)
      """,
      (image_id, channel),
    ).fetchone()

  if channel_row is None:
    raise HTTPException(status_code=404, detail="Channel not found")

  return DATA_ROOT / dict(channel_row)["filename"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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

class BBBC021ImportRequest(BaseModel):
  folder_path: str
  max_images: int | None = None

class JUMPImportRequest(BaseModel):
  folder_path: str

class MachineLearningTrainRequest(BaseModel):
  feature_set_id: int
  target: str
  algorithm: str
  cv_strategy: str = "stratified"
  cv_folds: int
  random_seed: int

class FeatureSetCreateRequest(BaseModel):
  name: str

  morphology: bool = True
  intensity: bool = True
  texture: bool = True

  foreground: str = "bright"

  remove_constant: bool = True
  remove_correlated: bool = False
  correlation_threshold: float = 0.95

  scaling: str = "none"

  pca_components: int = 0
  pca_mode: str = "add"

  umap_components: int = 0
  umap_mode: str = "add"

class DINOv2FeatureSetCreateRequest(BaseModel):
  name: str
  channel: str | None = None

class CombineFeatureSetsRequest(BaseModel):
  name: str
  feature_set_ids: list[int]

def _load_feature_set_as_image_rows(
  dataset_id: int,
  feature_set_id: int,
):
  with get_connection() as conn:
    feature_set_row = conn.execute(
      """
      SELECT
          id,
          dataset_id,
          name,
          configuration_json,
          feature_names_json
      FROM feature_sets
      WHERE id = ?
      """,
      (feature_set_id,),
    ).fetchone()

    if feature_set_row is None:
      raise HTTPException(
        status_code=404,
        detail=f"Feature set {feature_set_id} not found.",
      )

    feature_set = dict(feature_set_row)

    if feature_set["dataset_id"] != dataset_id:
      raise HTTPException(
        status_code=400,
        detail=(
          f"Feature set {feature_set_id} does not belong "
          "to the active dataset."
        ),
      )

    rows = conn.execute(
      """
      SELECT
          image_id,
          features_json
      FROM feature_set_rows
      WHERE feature_set_id = ?
      ORDER BY image_id, id
      """,
      (feature_set_id,),
    ).fetchall()

  configuration = json.loads(
    feature_set["configuration_json"]
  )

  feature_names = json.loads(
    feature_set["feature_names_json"]
  )

  aggregation_level = configuration.get(
    "aggregation_level",
    "object",
  )

  rows_by_image = {}

  for row in rows:
    image_id = int(row["image_id"])

    rows_by_image.setdefault(
      image_id,
      [],
    ).append(
      json.loads(row["features_json"])
    )

  image_features = {}

  if aggregation_level == "image":
    for image_id, stored_rows in rows_by_image.items():
      if len(stored_rows) != 1:
        raise HTTPException(
          status_code=400,
          detail=(
            f'Image-level Feature Set "{feature_set["name"]}" '
            f"contains {len(stored_rows)} rows for image {image_id}."
          ),
        )

      image_features[image_id] = {
        feature_name: float(
          stored_rows[0][feature_name]
        )
        for feature_name in feature_names
        if isinstance(
          stored_rows[0].get(feature_name),
          (int, float),
        )
      }

  else:
    for image_id, object_rows in rows_by_image.items():
      aggregated = {}

      for feature_name in feature_names:
        values = []

        for object_row in object_rows:
          value = object_row.get(feature_name)

          if isinstance(value, (int, float)):
            numeric_value = float(value)

            if np.isfinite(numeric_value):
              values.append(numeric_value)

        if not values:
          continue

        aggregated[f"{feature_name}_mean"] = float(
          np.mean(values)
        )

        aggregated[f"{feature_name}_std"] = float(
          np.std(values)
        )

        aggregated[f"{feature_name}_min"] = float(
          np.min(values)
        )

        aggregated[f"{feature_name}_max"] = float(
          np.max(values)
        )

      aggregated["num_objects"] = len(object_rows)

      image_features[image_id] = aggregated

  return {
    "id": feature_set["id"],
    "name": feature_set["name"],
    "configuration": configuration,
    "rows": image_features,
  }

@app.get("/experiments")
def get_experiments():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM experiments
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


@app.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM experiments
            WHERE id = ?
            """,
            (experiment_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Experiment not found",
        )

    return dict(row)


@app.post("/experiments")
def create_experiment(experiment: ExperimentCreate):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO experiments
            (
                name,
                domain,
                description,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                experiment.name,
                experiment.domain,
                experiment.description,
                "Draft",
            ),
        )

        experiment_id = cursor.lastrowid

        row = conn.execute(
            """
            SELECT *
            FROM experiments
            WHERE id = ?
            """,
            (experiment_id,),
        ).fetchone()

    return dict(row)

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

@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    return dict(row)


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


@app.get("/images/{image_id}/channels")
def get_image_channels(image_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM image_channels
            WHERE image_id = ?
            ORDER BY channel_order
            """,
            (image_id,),
        ).fetchall()

    return [dict(row) for row in rows]


@app.get("/datasets/{dataset_id}/images/{image_id}/preview")
def get_image_preview(
    dataset_id: int,
    image_id: int,
    channel: str | None = None,
):
    with get_connection() as conn:
        image_row = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ? AND id = ?
            """,
            (dataset_id, image_id),
        ).fetchone()

        if image_row is None:
            raise HTTPException(status_code=404, detail="Image not found")

        image_record = dict(image_row)

        if channel is not None:
            channel_row = conn.execute(
                """
                SELECT *
                FROM image_channels
                WHERE image_id = ?
                AND LOWER(channel_name) = LOWER(?)
                """,
                (image_id, channel),
            ).fetchone()

            if channel_row is None:
                raise HTTPException(status_code=404, detail="Channel not found")

            image_path = DATA_ROOT / dict(channel_row)["filename"]
        else:
            image_path = DATA_ROOT / image_record["filename"]

    image = load_image(image_path)
    image_array = pil_to_numpy(image)

    preview = normalize_for_display(image_array)

    if preview.ndim == 3:
        preview = preview[:, :, :3]

    output = BytesIO()
    Image.fromarray(preview).save(output, format="PNG")
    output.seek(0)

    return StreamingResponse(output, media_type="image/png")


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

@app.post("/datasets/{dataset_id}/import-bbbc021")
async def import_bbbc021(dataset_id: int, request: BBBC021ImportRequest):
    source_folder = Path(request.folder_path)

    if not source_folder.exists():
        raise HTTPException(status_code=404, detail="BBBC021 folder not found")

    importer = BBBC021Importer(source_folder)

    with get_connection() as conn:
        result = importer.import_to_database(
            dataset_id=dataset_id,
            data_root=DATA_ROOT,
            conn=conn,
            max_images=request.max_images,
        )

    return result

@app.post("/datasets/{dataset_id}/import-jump")
async def import_jump(
    dataset_id: int,
    request: JUMPImportRequest,
):
    source_folder = Path(
        request.folder_path
    )

    if not source_folder.exists():
        raise HTTPException(
            status_code=404,
            detail="JUMP dataset folder not found",
        )

    importer = JUMPImporter(
        source_folder
    )

    try:
        with get_connection() as conn:
            result = importer.import_to_database(
                dataset_id=dataset_id,
                data_root=DATA_ROOT,
                conn=conn,
            )

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return result

@app.get("/datasets/{dataset_id}/machine-learning/targets")
def get_machine_learning_targets(dataset_id: int):
    return get_available_targets(dataset_id)

@app.post("/datasets/{dataset_id}/machine-learning/train")
def train_machine_learning_model(
    dataset_id: int,
    request: MachineLearningTrainRequest,
):
    config = request.model_dump()

    return train_model(
        dataset_id=dataset_id,
        config=config,
    )

@app.get("/datasets/{dataset_id}/images/{image_id}/analysis")
def analyze_image(
  dataset_id: int,
  image_id: int,
  foreground: str = "bright",
  channel: str | None = None,
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
    image_path = resolve_image_path(image_record, image_id, channel)
    image = load_image(image_path)
    image_array = pil_to_numpy(image)
    gray = to_grayscale(image_array)

    binary, otsu_value = segment_otsu(
      gray,
      foreground=foreground,
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

@app.get("/datasets/{dataset_id}/images/{image_id}/intensity")
def analyze_image_intensity(
    dataset_id: int,
    image_id: int,
    foreground: str = "bright",
    channel: str | None = None,
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

    image_path = resolve_image_path(image_record, image_id, channel)

    image = load_image(image_path)
    image_array = pil_to_numpy(image)

    gray = to_grayscale(image_array)

    binary, otsu_value = segment_otsu(
        gray,
        foreground=foreground,
        return_threshold=True,
    )

    labels = connected_components(binary)

    intensity = measure_intensity(labels, gray)
    summary = summarize_intensity(intensity)

    return {
        "dataset_id": dataset_id,
        "image_id": image_id,
        "filename": image_record["filename"],
        "threshold": otsu_value,
        "num_objects": len(intensity),
        "summary": summary,
        "objects": intensity,
    }

@app.get("/datasets/{dataset_id}/images/{image_id}/texture")
def analyze_image_texture(
    dataset_id: int,
    image_id: int,
    foreground: str = "bright",
    channel: str | None = None,
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
    image_path = resolve_image_path(image_record, image_id, channel)

    image = load_image(image_path)
    image_array = pil_to_numpy(image)
    gray = to_grayscale(image_array)

    binary, otsu_value = segment_otsu(
        gray,
        foreground=foreground,
        return_threshold=True,
    )

    labels = connected_components(binary)

    texture = measure_texture(labels, gray)
    summary = summarize_texture(texture)

    return {
        "dataset_id": dataset_id,
        "image_id": image_id,
        "filename": image_record["filename"],
        "threshold": otsu_value,
        "num_objects": len(texture),
        "summary": summary,
        "objects": texture,
    }

@app.get("/datasets/{dataset_id}/features")
def build_dataset_features(
    dataset_id: int,
    morphology: bool = True,
    intensity: bool = True,
    texture: bool = True,
    foreground: str = "bright",
    remove_constant: bool = True,
    remove_correlated: bool = False,
    correlation_threshold: float = 0.95,
    scaling: str = "none",
    pca_components: int = 0,
    pca_mode: str = "add",
    umap_components: int = 0,
    umap_mode: str = "add",
):
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

    features = []
    images_processed = 0

    for row in rows:
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

        morphology_by_label = {}
        intensity_by_label = {}
        texture_by_label = {}

        if morphology:
            morphology_by_label = {
                item["label"]: item
                for item in measure_regions(labels)
            }

        if intensity:
            intensity_by_label = {
                item["label"]: item
                for item in measure_intensity(labels, gray)
            }

        if texture:
            texture_by_label = {
                item["label"]: item
                for item in measure_texture(labels, gray)
            }

        all_labels = sorted(
            set(morphology_by_label.keys())
            | set(intensity_by_label.keys())
            | set(texture_by_label.keys())
        )

        for label in all_labels:
            row_features = {
                "dataset_id": dataset_id,
                "image_id": image_record["id"],
                "filename": image_record["filename"],
                "label": label,
            }

            if morphology and label in morphology_by_label:
                morphology_features = morphology_by_label[label].copy()

                centroid = morphology_features.pop("centroid", None)
                if centroid is not None:
                    morphology_features["centroid_row"] = centroid["row"]
                    morphology_features["centroid_col"] = centroid["col"]

                bbox = morphology_features.pop("bbox", None)
                if bbox is not None:
                    morphology_features["bbox_min_row"] = bbox["min_row"]
                    morphology_features["bbox_min_col"] = bbox["min_col"]
                    morphology_features["bbox_max_row"] = bbox["max_row"]
                    morphology_features["bbox_max_col"] = bbox["max_col"]

                row_features.update(morphology_features)

            if intensity and label in intensity_by_label:
                row_features.update(intensity_by_label[label])

            if texture and label in texture_by_label:
                row_features.update(texture_by_label[label])

            features.append(row_features)

        images_processed += 1

    feature_names = sorted(
      {
        key
        for item in features
        for key in item.keys()
        if key not in {"dataset_id", "image_id", "filename", "label"}
      }
    )

    removed_constant_features = []

    if remove_constant and features:
      constant_features = []

      for feature_name in feature_names:
        values = [
          item.get(feature_name)
          for item in features
          if isinstance(item.get(feature_name), (int, float))
        ]

        if not values:
          continue

        unique_values = set(values)

        if len(unique_values) == 1:
          constant_features.append(feature_name)

      if constant_features:
        for item in features:
          for feature_name in constant_features:
            item.pop(feature_name, None)

        removed_constant_features = constant_features
        feature_names = [
          feature_name
          for feature_name in feature_names
          if feature_name not in constant_features
        ]

    removed_correlated_features = []
    PROTECTED_CORRELATION_FEATURES = {
      "centroid_row",
      "centroid_col",
      "bbox_min_row",
      "bbox_min_col",
      "bbox_max_row",
      "bbox_max_col",
    }

    if remove_correlated and features:
      numeric_features = []

      for feature_name in feature_names:
        values = [
          item.get(feature_name)
          for item in features
          if isinstance(item.get(feature_name), (int, float))
        ]

        if len(values) == len(features):
          numeric_features.append(feature_name)

      if len(numeric_features) > 1:
        matrix = np.array(
          [
            [item[feature_name] for feature_name in numeric_features]
            for item in features
          ],
          dtype=float,
        )

        correlation_matrix = np.corrcoef(matrix, rowvar=False)

        features_to_remove = set()

        for i in range(len(numeric_features)):
          for j in range(i + 1, len(numeric_features)):
            correlation_value = correlation_matrix[i, j]

            if np.isnan(correlation_value):
              continue

            if abs(correlation_value) >= correlation_threshold:
              candidate_feature = numeric_features[j]

              if candidate_feature not in PROTECTED_CORRELATION_FEATURES:
                features_to_remove.add(candidate_feature)

        if features_to_remove:
          removed_correlated_features = sorted(features_to_remove)

          for item in features:
            for feature_name in removed_correlated_features:
              item.pop(feature_name, None)

          feature_names = [
            feature_name
            for feature_name in feature_names
            if feature_name not in features_to_remove
          ]

    scaled_features = []

    if scaling != "none" and features:
      numeric_features = []

      for feature_name in feature_names:
        values = [
          item.get(feature_name)
          for item in features
          if isinstance(item.get(feature_name), (int, float))
        ]

        if len(values) == len(features):
          numeric_features.append(feature_name)

      if numeric_features:
        matrix = np.array(
          [
            [item[feature_name] for feature_name in numeric_features]
            for item in features
          ],
          dtype=float,
        )

        if scaling == "standard":
          scaler = StandardScaler()
        elif scaling == "minmax":
          scaler = MinMaxScaler()
        elif scaling == "robust":
          scaler = RobustScaler()
        else:
          raise HTTPException(
            status_code=400,
            detail="Unsupported scaling method",
          )

        scaled_matrix = scaler.fit_transform(matrix)

        for row_index, item in enumerate(features):
          for column_index, feature_name in enumerate(numeric_features):
            item[feature_name] = float(
              scaled_matrix[row_index, column_index]
            )

        scaled_features = numeric_features

    pca_result = None

    if pca_components > 0 and features:
      numeric_features = []

      for feature_name in feature_names:
        values = [
          item.get(feature_name)
          for item in features
          if isinstance(item.get(feature_name), (int, float))
        ]

        if len(values) == len(features):
          numeric_features.append(feature_name)

      if len(numeric_features) >= pca_components:
        matrix = np.array(
          [
            [item[feature_name] for feature_name in numeric_features]
            for item in features
          ],
          dtype=float,
        )

        pca = PCA(n_components=pca_components)
        pca_matrix = pca.fit_transform(matrix)

        pca_feature_names = []

        for component_index in range(pca_components):
          pca_feature_name = f"pca_{component_index + 1}"
          pca_feature_names.append(pca_feature_name)

          for row_index, item in enumerate(features):
            item[pca_feature_name] = float(
              pca_matrix[row_index, component_index]
            )

        if pca_mode == "add":
          feature_names.extend(pca_feature_names)

        elif pca_mode == "replace":
          for item in features:
            for feature_name in numeric_features:
              item.pop(feature_name, None)

          feature_names = [
            feature_name
            for feature_name in feature_names
            if feature_name not in numeric_features
          ]

          feature_names.extend(pca_feature_names)

        else:
          raise HTTPException(
            status_code=400,
            detail="Unsupported PCA mode",
          )

        pca_result = {
          "components": pca_components,
          "features": pca_feature_names,
          "explained_variance_ratio": [
            float(value)
            for value in pca.explained_variance_ratio_
          ],
          "total_explained_variance": float(
            np.sum(pca.explained_variance_ratio_)
          ),
          "mode": pca_mode,
          "input_features": numeric_features,
        }

    umap_result = None

    if umap_components > 0 and features:
      numeric_features = []

      for feature_name in feature_names:
        values = [
          item.get(feature_name)
          for item in features
          if isinstance(item.get(feature_name), (int, float))
        ]

        if len(values) == len(features):
          numeric_features.append(feature_name)

      if len(numeric_features) >= umap_components:
        matrix = np.array(
          [
            [item[feature_name] for feature_name in numeric_features]
            for item in features
          ],
          dtype=float,
        )

        reducer = umap.UMAP(
          n_components=umap_components,
          random_state=42,
        )

        umap_matrix = reducer.fit_transform(matrix)

        umap_feature_names = []

        for component_index in range(umap_components):
          umap_feature_name = f"umap_{component_index + 1}"
          umap_feature_names.append(umap_feature_name)

          for row_index, item in enumerate(features):
            item[umap_feature_name] = float(
              umap_matrix[row_index, component_index]
            )

        if umap_mode == "add":
          feature_names.extend(umap_feature_names)

        elif umap_mode == "replace":
          for item in features:
            for feature_name in numeric_features:
              item.pop(feature_name, None)

          feature_names = [
            feature_name
            for feature_name in feature_names
            if feature_name not in numeric_features
          ]

          feature_names.extend(umap_feature_names)

        else:
          raise HTTPException(
            status_code=400,
            detail="Unsupported UMAP mode",
          )

        umap_result = {
          "components": umap_components,
          "features": umap_feature_names,
          "mode": umap_mode,
          "input_features": numeric_features,
        }

    return {
        "dataset_id": dataset_id,
        "images_processed": images_processed,
        "num_objects": len(features),
        "num_features": len(feature_names),
        "feature_names": feature_names,
        "features": features,
        "feature_groups": {
            "morphology": morphology,
            "intensity": intensity,
            "texture": texture,
        },
        "removed_features": {
          "constant": removed_constant_features,
          "correlated": removed_correlated_features,
        },
        "status": "ready",
        "scaling": scaling,
        "scaled_features": scaled_features,
        "pca": pca_result,
        "umap": umap_result,
    }

@app.post("/datasets/{dataset_id}/feature-sets")
def create_feature_set(
    dataset_id: int,
    request: FeatureSetCreateRequest,
):
    feature_set_name = request.name.strip()

    if not feature_set_name:
        raise HTTPException(
            status_code=400,
            detail="Feature set name is required.",
        )

    with get_connection() as conn:
        dataset_row = conn.execute(
            """
            SELECT id
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()

    if dataset_row is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )

    with get_connection() as conn:
        existing_feature_set = conn.execute(
            """
            SELECT id
            FROM feature_sets
            WHERE dataset_id = ?
            AND LOWER(name) = LOWER(?)
            """,
            (
                dataset_id,
                feature_set_name,
            ),
        ).fetchone()

    if existing_feature_set is not None:
        raise HTTPException(
            status_code=409,
            detail=f'A feature set named "{feature_set_name}" already exists.',
        )

    configuration = request.model_dump(
        exclude={"name"},
    )

    result = build_dataset_features(
        dataset_id=dataset_id,
        morphology=request.morphology,
        intensity=request.intensity,
        texture=request.texture,
        foreground=request.foreground,
        remove_constant=request.remove_constant,
        remove_correlated=request.remove_correlated,
        correlation_threshold=request.correlation_threshold,
        scaling=request.scaling,
        pca_components=request.pca_components,
        pca_mode=request.pca_mode,
        umap_components=request.umap_components,
        umap_mode=request.umap_mode,
    )

    feature_names = result["feature_names"]
    feature_rows = result["features"]

    if not feature_rows:
        raise HTTPException(
            status_code=400,
            detail="The generated feature set contains no rows.",
        )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO feature_sets
            (
                dataset_id,
                name,
                configuration_json,
                feature_names_json,
                num_rows,
                num_features
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                feature_set_name,
                json.dumps(configuration, sort_keys=True),
                json.dumps(feature_names),
                len(feature_rows),
                len(feature_names),
            ),
        )

        feature_set_id = cursor.lastrowid

        rows_to_insert = []

        for feature_row in feature_rows:
            image_id = feature_row.get("image_id")
            object_label = feature_row.get("label")

            stored_features = {
                feature_name: feature_row.get(feature_name)
                for feature_name in feature_names
            }

            rows_to_insert.append(
                (
                    feature_set_id,
                    image_id,
                    object_label,
                    json.dumps(
                        stored_features,
                        sort_keys=True,
                    ),
                )
            )

        conn.executemany(
            """
            INSERT INTO feature_set_rows
            (
                feature_set_id,
                image_id,
                object_label,
                features_json
            )
            VALUES (?, ?, ?, ?)
            """,
            rows_to_insert,
        )

    return {
        **result,
        "feature_set_id": feature_set_id,
        "name": feature_set_name,
        "configuration": configuration,
        "persisted": True,
    }

@app.post("/datasets/{dataset_id}/feature-sets/dinov2")
def create_dinov2_feature_set(
    dataset_id: int,
    request: DINOv2FeatureSetCreateRequest,
):
    feature_set_name = request.name.strip()

    if not feature_set_name:
        raise HTTPException(
            status_code=400,
            detail="Feature set name is required.",
        )

    with get_connection() as conn:
        dataset_row = conn.execute(
            """
            SELECT id
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()

        if dataset_row is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        existing_feature_set = conn.execute(
            """
            SELECT id
            FROM feature_sets
            WHERE dataset_id = ?
            AND LOWER(name) = LOWER(?)
            """,
            (
                dataset_id,
                feature_set_name,
            ),
        ).fetchone()

        if existing_feature_set is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f'A feature set named "{feature_set_name}" '
                    "already exists."
                ),
            )

        image_rows = conn.execute(
            """
            SELECT *
            FROM images
            WHERE dataset_id = ?
            ORDER BY id
            """,
            (dataset_id,),
        ).fetchall()

    if not image_rows:
        raise HTTPException(
            status_code=400,
            detail="The dataset contains no images.",
        )

    model = get_dinov2_model()

    feature_names = [
        f"dinov2_{index}"
        for index in range(1, 769)
    ]

    generated_rows = []

    for image_row in image_rows:
        image_record = dict(image_row)
        image_id = int(image_record["id"])

        if request.channel:
            with get_connection() as conn:
                channel_row = conn.execute(
                    """
                    SELECT filename
                    FROM image_channels
                    WHERE image_id = ?
                    AND LOWER(channel_name) = LOWER(?)
                    """,
                    (
                        image_id,
                        request.channel,
                    ),
                ).fetchone()

            if channel_row is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f'Channel "{request.channel}" was not found '
                        f"for image {image_id}."
                    ),
                )

            image_filename = channel_row["filename"]
        else:
            image_filename = image_record["filename"]

        image_path = DATA_ROOT / image_filename

        if not image_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Image file not found: {image_path}",
            )

        image = Image.open(image_path)

        try:
            embedding = model.embed(image)
        finally:
            image.close()

        embedding = np.asarray(
            embedding,
            dtype=np.float32,
        ).reshape(-1)

        if embedding.shape[0] != 768:
            raise HTTPException(
                status_code=500,
                detail=(
                    "DINOv2 produced an unexpected embedding "
                    f"size: {embedding.shape[0]}."
                ),
            )

        embedding_features = {
            feature_name: float(value)
            for feature_name, value in zip(
                feature_names,
                embedding,
            )
        }

        generated_rows.append(
            (
                image_id,
                embedding_features,
            )
        )

    configuration = {
        "extractor": "dinov2",
        "model_name": model.model_name,
        "channel": request.channel,
        "aggregation_level": "image",
        "embedding_size": 768,
    }

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO feature_sets
            (
                dataset_id,
                name,
                configuration_json,
                feature_names_json,
                num_rows,
                num_features
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                feature_set_name,
                json.dumps(
                    configuration,
                    sort_keys=True,
                ),
                json.dumps(feature_names),
                len(generated_rows),
                len(feature_names),
            ),
        )

        feature_set_id = cursor.lastrowid

        conn.executemany(
            """
            INSERT INTO feature_set_rows
            (
                feature_set_id,
                image_id,
                object_label,
                features_json
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    feature_set_id,
                    image_id,
                    None,
                    json.dumps(
                        embedding_features,
                        sort_keys=True,
                    ),
                )
                for image_id, embedding_features
                in generated_rows
            ],
        )

    return {
        "feature_set_id": feature_set_id,
        "dataset_id": dataset_id,
        "name": feature_set_name,
        "configuration": configuration,
        "feature_names": feature_names,
        "num_rows": len(generated_rows),
        "num_features": len(feature_names),
        "images_processed": len(generated_rows),
        "persisted": True,
        "status": "ready",
    }

@app.post("/datasets/{dataset_id}/feature-sets/combine")
def combine_feature_sets(
    dataset_id: int,
    request: CombineFeatureSetsRequest,
):
    combined_name = request.name.strip()

    if not combined_name:
        raise HTTPException(
            status_code=400,
            detail="Combined Feature Set name is required.",
        )

    if len(request.feature_set_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Select at least two Feature Sets to combine.",
        )

    if len(set(request.feature_set_ids)) != len(
        request.feature_set_ids
    ):
        raise HTTPException(
            status_code=400,
            detail="The same Feature Set cannot be selected twice.",
        )

    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM feature_sets
            WHERE dataset_id = ?
            AND LOWER(name) = LOWER(?)
            """,
            (
                dataset_id,
                combined_name,
            ),
        ).fetchone()

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f'A feature set named "{combined_name}" '
                "already exists."
            ),
        )

    source_sets = [
        _load_feature_set_as_image_rows(
            dataset_id=dataset_id,
            feature_set_id=feature_set_id,
        )
        for feature_set_id in request.feature_set_ids
    ]

    common_image_ids = set(
        source_sets[0]["rows"].keys()
    )

    for source_set in source_sets[1:]:
        common_image_ids &= set(
            source_set["rows"].keys()
        )

    if not common_image_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "The selected Feature Sets have no images in common."
            ),
        )

    combined_rows = []
    combined_feature_names = []

    for source_index, source_set in enumerate(
        source_sets,
        start=1,
    ):
        example_image_id = next(
            iter(common_image_ids)
        )

        source_feature_names = sorted(
            source_set["rows"][example_image_id].keys()
        )

        for feature_name in source_feature_names:
            combined_feature_names.append(
                f"source{source_index}__{feature_name}"
            )

    for image_id in sorted(common_image_ids):
        combined_features = {}

        for source_index, source_set in enumerate(
            source_sets,
            start=1,
        ):
            source_features = source_set["rows"][
                image_id
            ]

            for feature_name, value in source_features.items():
                combined_features[
                    f"source{source_index}__{feature_name}"
                ] = float(value)

        combined_rows.append(
            (
                image_id,
                combined_features,
            )
        )

    configuration = {
        "extractor": "combined",
        "aggregation_level": "image",
        "source_feature_set_ids": request.feature_set_ids,
        "source_feature_set_names": [
            source_set["name"]
            for source_set in source_sets
        ],
    }

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO feature_sets
            (
                dataset_id,
                name,
                configuration_json,
                feature_names_json,
                num_rows,
                num_features
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                combined_name,
                json.dumps(
                    configuration,
                    sort_keys=True,
                ),
                json.dumps(combined_feature_names),
                len(combined_rows),
                len(combined_feature_names),
            ),
        )

        feature_set_id = cursor.lastrowid

        conn.executemany(
            """
            INSERT INTO feature_set_rows
            (
                feature_set_id,
                image_id,
                object_label,
                features_json
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    feature_set_id,
                    image_id,
                    None,
                    json.dumps(
                        features,
                        sort_keys=True,
                    ),
                )
                for image_id, features
                in combined_rows
            ],
        )

    return {
        "feature_set_id": feature_set_id,
        "dataset_id": dataset_id,
        "name": combined_name,
        "num_rows": len(combined_rows),
        "num_features": len(combined_feature_names),
        "configuration": configuration,
        "persisted": True,
        "status": "ready",
    }

@app.get("/datasets/{dataset_id}/feature-sets")
def get_feature_sets(dataset_id: int):
    with get_connection() as conn:
        dataset_row = conn.execute(
            """
            SELECT id
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()

        if dataset_row is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        rows = conn.execute(
            """
            SELECT
                id,
                dataset_id,
                name,
                configuration_json,
                feature_names_json,
                num_rows,
                num_features,
                created_at
            FROM feature_sets
            WHERE dataset_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (dataset_id,),
        ).fetchall()

    feature_sets = []

    for row in rows:
        feature_set = dict(row)

        feature_set["configuration"] = json.loads(
            feature_set.pop("configuration_json")
        )

        feature_set["feature_names"] = json.loads(
            feature_set.pop("feature_names_json")
        )

        feature_sets.append(feature_set)

    return feature_sets

@app.get("/datasets/{dataset_id}/images/{image_id}/overlay")
def get_image_overlay(
    dataset_id: int,
    image_id: int,
    foreground: str = "bright",
    channel: str | None = None,
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
    image_path = resolve_image_path(image_record, image_id, channel)
    image = load_image(image_path)
    image_array = pil_to_numpy(image)

    gray = to_grayscale(image_array)
    binary, threshold = segment_otsu(
      gray,
      foreground=foreground,
      return_threshold=True,
    )

    display_image = normalize_for_display(image_array)

    if display_image.ndim == 2:
        rgb_image = np.stack([display_image] * 3, axis=-1)
    else:
        rgb_image = display_image[:, :, :3]

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
    channel: str | None = None,
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
    image_path = resolve_image_path(image_record, image_id, channel)
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

    display_image = normalize_for_display(image_array)

    if display_image.ndim == 2:
        rgb_image = np.stack([display_image] * 3, axis=-1)
    else:
        rgb_image = display_image[:, :, :3]

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
    channel: str | None = None,
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

    image_path = resolve_image_path(image_record, image_id, channel)
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

@app.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int):
    with get_connection() as conn:
        dataset_row = conn.execute(
            """
            SELECT id, name
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()

        if dataset_row is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        feature_set_rows = conn.execute(
            """
            SELECT id
            FROM feature_sets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchall()

        feature_set_ids = [
            row["id"]
            for row in feature_set_rows
        ]

        if feature_set_ids:
            placeholders = ",".join(
                "?"
                for _ in feature_set_ids
            )

            conn.execute(
                f"""
                DELETE FROM feature_set_rows
                WHERE feature_set_id IN ({placeholders})
                """,
                feature_set_ids,
            )

        conn.execute(
            """
            DELETE FROM feature_sets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        )

        image_rows = conn.execute(
            """
            SELECT id
            FROM images
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchall()

        image_ids = [
            row["id"]
            for row in image_rows
        ]

        if image_ids:
            placeholders = ",".join(
                "?"
                for _ in image_ids
            )

            conn.execute(
                f"""
                DELETE FROM image_channels
                WHERE image_id IN ({placeholders})
                """,
                image_ids,
            )

        conn.execute(
            """
            DELETE FROM images
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        )

        conn.execute(
            """
            DELETE FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

    return {
        "dataset_id": dataset_id,
        "name": dataset_row["name"],
        "status": "deleted",
    }

@app.delete("/feature-sets/{feature_set_id}")
def delete_feature_set(feature_set_id: int):
    with get_connection() as conn:
        feature_set = conn.execute(
            """
            SELECT id, name
            FROM feature_sets
            WHERE id = ?
            """,
            (feature_set_id,),
        ).fetchone()

        if feature_set is None:
            raise HTTPException(
                status_code=404,
                detail="Feature set not found.",
            )

        conn.execute(
            """
            DELETE FROM feature_set_rows
            WHERE feature_set_id = ?
            """,
            (feature_set_id,),
        )

        conn.execute(
            """
            DELETE FROM feature_sets
            WHERE id = ?
            """,
            (feature_set_id,),
        )

    return {
        "feature_set_id": feature_set_id,
        "name": feature_set["name"],
        "status": "deleted",
    }