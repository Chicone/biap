from collections import Counter
from pathlib import Path
import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import (
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_val_predict,
)
from db import get_connection
from vision.io import load_image, pil_to_numpy
from vision.preprocessing import to_grayscale
from vision.segmentation import segment_otsu, connected_components
from vision.measurements import (
    measure_regions,
    measure_intensity,
    measure_texture,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = BASE_DIR / "data" / "raw"


def _get_channel_filename(image_id: int, channel_name: str | None):
    if not channel_name:
        return None

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT filename
            FROM image_channels
            WHERE image_id = ?
            AND LOWER(channel_name) = LOWER(?)
            """,
            (image_id, channel_name),
        ).fetchone()

    if row is None:
        return None

    return row["filename"]


def _flatten_object_features(objects, prefix):
    if not objects:
        return {}

    numeric_values = {}

    for item in objects:
        for key, value in item.items():
            if key == "label":
                continue

            if isinstance(value, (int, float)):
                numeric_values.setdefault(key, []).append(float(value))

    flattened = {}

    for key, values in numeric_values.items():
        flattened[f"{prefix}_{key}_mean"] = float(np.mean(values))
        flattened[f"{prefix}_{key}_std"] = float(np.std(values))
        flattened[f"{prefix}_{key}_min"] = float(np.min(values))
        flattened[f"{prefix}_{key}_max"] = float(np.max(values))

    return flattened


def _extract_image_features(image_record, config):
    image_id = image_record["id"]

    channel_name = config.get("channel")
    foreground = config.get("foreground", "bright")
    feature_config = config.get("features", {})
    aggregation_level = config.get("aggregation_level", "image")

    cache_key = json.dumps(feature_config, sort_keys=True)

    with get_connection() as conn:
        cached_row = conn.execute(
            """
            SELECT features_json
            FROM image_feature_cache
            WHERE image_id = ?
            AND COALESCE(channel_name, '') = COALESCE(?, '')
            AND foreground = ?
            AND aggregation_level = ?
            AND feature_config = ?
            """,
            (
                image_id,
                channel_name,
                foreground,
                aggregation_level,
                cache_key,
            ),
        ).fetchone()

    if cached_row is not None:
        return json.loads(cached_row["features_json"])


    channel_filename = _get_channel_filename(image_id, channel_name)

    filename = channel_filename or image_record["filename"]
    image_path = DATA_ROOT / filename

    image = load_image(image_path)
    image_array = pil_to_numpy(image)
    gray = to_grayscale(image_array)

    binary, _ = segment_otsu(
        gray,
        foreground=foreground,
        return_threshold=True,
    )

    labels = connected_components(binary)

    features = {}

    if feature_config.get("morphology", True):
        morphology = measure_regions(labels)
        features.update(_flatten_object_features(morphology, "morphology"))

    if feature_config.get("intensity", True):
        intensity = measure_intensity(labels, gray)
        features.update(_flatten_object_features(intensity, "intensity"))

    if feature_config.get("texture", True):
        texture = measure_texture(labels, gray)
        features.update(_flatten_object_features(texture, "texture"))

    features["num_objects"] = int(labels.max())

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO image_feature_cache
            (
                image_id,
                channel_name,
                foreground,
                aggregation_level,
                feature_config,
                features_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                image_id,
                channel_name,
                foreground,
                aggregation_level,
                cache_key,
                json.dumps(features, sort_keys=True),
            ),
        )

    return features


def _build_dataset(dataset_id: int, config: dict):
  target_name = config.get("target", "moa")

  allowed_targets = {"moa", "compound", "concentration"}

  if target_name not in allowed_targets:
    raise ValueError(f"Unsupported target: {target_name}")

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

  feature_rows = []
  targets = []
  image_ids = []
  groups = []

  for row in rows:
    image_record = dict(row)
    target_value = image_record.get(target_name)

    if target_value is None or target_value == "":
      continue

    features = _extract_image_features(image_record, config)

    if not features:
      continue

    plate = image_record.get("plate")
    well = image_record.get("well")

    if plate and well:
      group_name = f"{plate}::{well}"
    else:
      group_name = None

    feature_rows.append(features)
    targets.append(str(target_value))
    image_ids.append(image_record["id"])
    groups.append(group_name)

  if not feature_rows:
    raise ValueError("No valid feature rows were generated.")

  feature_names = sorted(
    {
      key
      for feature_row in feature_rows
      for key in feature_row.keys()
    }
  )

  matrix = np.array(
    [
      [
        feature_row.get(feature_name, 0.0)
        for feature_name in feature_names
      ]
      for feature_row in feature_rows
    ],
    dtype=float,
  )

  return (
    matrix,
    np.array(targets),
    feature_names,
    image_ids,
    np.array(groups, dtype=object),
  )

def train_model(dataset_id: int, config: dict):
  algorithm = config.get("algorithm", "random_forest")

  if algorithm != "random_forest":
    raise ValueError(f"Unsupported algorithm: {algorithm}")

  (
    X,
    y,
    feature_names,
    image_ids,
    groups,
  ) = _build_dataset(dataset_id, config)

  class_counts = Counter(y)

  if len(class_counts) < 2:
    raise ValueError(
      "Evaluation requires at least two target classes."
    )

  random_seed = config.get("random_seed", 42)
  requested_cv_folds = config.get("cv_folds", 5)
  cv_strategy = config.get("cv_strategy", "stratified")

  if requested_cv_folds < 2:
    raise ValueError(
      "Cross-validation requires at least two folds."
    )

  model = RandomForestClassifier(
    n_estimators=200,
    random_state=random_seed,
    class_weight="balanced",
    n_jobs=-1,
  )

  labels = sorted(class_counts.keys())

  if cv_strategy == "stratified":
    min_class_count = min(class_counts.values())

    usable_cv_folds = min(
      requested_cv_folds,
      min_class_count,
    )

    if usable_cv_folds < 2:
      raise ValueError(
        "Not enough samples per class for stratified "
        "cross-validation."
      )

    cv = StratifiedKFold(
      n_splits=usable_cv_folds,
      shuffle=True,
      random_state=random_seed,
    )

    y_pred = cross_val_predict(
      model,
      X,
      y,
      cv=cv,
      n_jobs=-1,
    )

    evaluation_name = (
      f"{usable_cv_folds}-fold stratified cross-validation"
    )

    num_groups = None

  elif cv_strategy == "group_well":
    missing_group_indices = [
      index
      for index, group in enumerate(groups)
      if group is None
    ]

    if missing_group_indices:
      raise ValueError(
        "Well-aware cross-validation requires plate and well "
        "metadata for every evaluated image."
      )

    unique_groups = np.unique(groups)

    if len(unique_groups) < 2:
      raise ValueError(
        "Well-aware cross-validation requires at least two wells."
      )

    groups_per_class = {}

    for class_name in labels:
      class_groups = np.unique(groups[y == class_name])
      groups_per_class[class_name] = len(class_groups)

    min_groups_per_class = min(groups_per_class.values())

    usable_cv_folds = min(
      requested_cv_folds,
      len(unique_groups),
      min_groups_per_class,
    )

    if usable_cv_folds < 2:
      raise ValueError(
        "Each class must appear in at least two different wells "
        "for well-aware cross-validation."
      )

    cv = StratifiedGroupKFold(
      n_splits=usable_cv_folds,
      shuffle=True,
      random_state=random_seed,
    )

    y_pred = cross_val_predict(
      model,
      X,
      y,
      cv=cv,
      groups=groups,
      n_jobs=-1,
    )

    evaluation_name = (
      f"{usable_cv_folds}-fold stratified group "
      "cross-validation by well"
    )

    num_groups = int(len(unique_groups))

  else:
    raise ValueError(
      f"Unsupported cross-validation strategy: {cv_strategy}"
    )

  accuracy = accuracy_score(y, y_pred)

  report = classification_report(
    y,
    y_pred,
    labels=labels,
    output_dict=True,
    zero_division=0,
  )

  confusion = confusion_matrix(
    y,
    y_pred,
    labels=labels,
  )

  # Train the final deployable model on all available samples.
  model.fit(X, y)

  importances = model.feature_importances_

  feature_importance = sorted(
    [
      {
        "feature": feature_name,
        "importance": float(importance),
      }
      for feature_name, importance in zip(
      feature_names,
      importances,
    )
    ],
    key=lambda item: item["importance"],
    reverse=True,
  )

  predictions = [
    {
      "image_id": int(image_id),
      "actual": str(actual),
      "predicted": str(predicted),
      "correct": bool(actual == predicted),
      "group": (
        str(group)
        if group is not None
        else None
      ),
    }
    for image_id, actual, predicted, group in zip(
      image_ids,
      y,
      y_pred,
      groups,
    )
  ]

  return {
    "dataset_id": dataset_id,
    "status": "evaluated",
    "algorithm": algorithm,
    "target": config.get("target", "moa"),
    "num_samples": int(X.shape[0]),
    "num_features": int(X.shape[1]),
    "num_classes": len(class_counts),
    "class_counts": dict(class_counts),
    "accuracy": float(accuracy),
    "classification_report": report,
    "confusion_matrix": confusion.tolist(),
    "labels": labels,
    "cross_validation": {
      "strategy": cv_strategy,
      "name": evaluation_name,
      "folds": int(usable_cv_folds),
      "num_groups": num_groups,
    },
    "predictions": predictions,
    "top_features": feature_importance[:20],
    "image_ids": image_ids,
  }