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


class BBBC021ImportRequest(BaseModel):
  folder_path: str
  max_images: int | None = None

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

@app.get("/datasets/{dataset_id}/images/{image_id}/intensity")
def analyze_image_intensity(
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

