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

def _load_feature_set_dataset(
    dataset_id: int,
    feature_set_id: int,
    target_name: str,
):
  allowed_targets = {
    "moa",
    "compound",
    "concentration",
  }

  if target_name not in allowed_targets:
    raise ValueError(
      f"Unsupported target: {target_name}"
    )

  with get_connection() as conn:
    feature_set_row = conn.execute(
      """
      SELECT
        id,
        dataset_id,
        name,
        feature_names_json,
        configuration_json
      FROM feature_sets
      WHERE id = ?
      """,
      (feature_set_id,),
    ).fetchone()

    if feature_set_row is None:
      raise ValueError(
        f"Feature set {feature_set_id} was not found."
      )

    feature_set_record = dict(feature_set_row)

    if feature_set_record["dataset_id"] != dataset_id:
      raise ValueError(
        "The selected Feature Set does not belong to "
        "the active dataset."
      )

    stored_rows = conn.execute(
      """
      SELECT
        feature_set_rows.image_id,
        feature_set_rows.features_json,
        images.plate,
        images.well,
        images.moa,
        images.compound,
        images.concentration
      FROM feature_set_rows
      JOIN images
        ON images.id = feature_set_rows.image_id
      WHERE feature_set_rows.feature_set_id = ?
      ORDER BY
        feature_set_rows.image_id,
        feature_set_rows.id
      """,
      (feature_set_id,),
    ).fetchall()

  if not stored_rows:
    raise ValueError(
      "The selected Feature Set contains no stored rows."
    )

  stored_feature_names = json.loads(
    feature_set_record["feature_names_json"]
  )

  if not stored_feature_names:
    raise ValueError(
      "The selected Feature Set contains no features."
    )

  rows_by_image = {}

  for row in stored_rows:
    record = dict(row)
    image_id = int(record["image_id"])

    image_entry = rows_by_image.setdefault(
      image_id,
      {
        "object_features": [],
        "target": record.get(target_name),
        "plate": record.get("plate"),
        "well": record.get("well"),
      },
    )

    row_features = json.loads(
      record["features_json"]
    )

    image_entry["object_features"].append(
      row_features
    )

  aggregated_rows = []
  targets = []
  image_ids = []
  groups = []

  for image_id, image_entry in rows_by_image.items():
    target_value = image_entry["target"]

    if target_value is None or target_value == "":
      continue

    object_features = image_entry["object_features"]

    aggregated_features = {}

    for feature_name in stored_feature_names:
      values = []

      for object_row in object_features:
        value = object_row.get(feature_name)

        if isinstance(value, (int, float)):
          numeric_value = float(value)

          if np.isfinite(numeric_value):
            values.append(numeric_value)

      if not values:
        continue

      aggregated_features[
        f"{feature_name}_mean"
      ] = float(np.mean(values))

      aggregated_features[
        f"{feature_name}_std"
      ] = float(np.std(values))

      aggregated_features[
        f"{feature_name}_min"
      ] = float(np.min(values))

      aggregated_features[
        f"{feature_name}_max"
      ] = float(np.max(values))

    aggregated_features["num_objects"] = int(
      len(object_features)
    )

    if not aggregated_features:
      continue

    plate = image_entry["plate"]
    well = image_entry["well"]

    group_name = (
      f"{plate}::{well}"
      if plate and well
      else None
    )

    aggregated_rows.append(aggregated_features)
    targets.append(str(target_value))
    image_ids.append(image_id)
    groups.append(group_name)

  if not aggregated_rows:
    raise ValueError(
      "No images with valid targets and Feature Set "
      "rows were available for evaluation."
    )

  aggregated_feature_names = sorted(
    {
      feature_name
      for aggregated_row in aggregated_rows
      for feature_name in aggregated_row.keys()
    }
  )

  matrix = np.array(
    [
      [
        aggregated_row.get(
          feature_name,
          0.0,
        )
        for feature_name
        in aggregated_feature_names
      ]
      for aggregated_row in aggregated_rows
    ],
    dtype=float,
  )

  return (
    matrix,
    np.array(targets),
    aggregated_feature_names,
    image_ids,
    np.array(groups, dtype=object),
    feature_set_record,
  )

def train_model(dataset_id: int, config: dict):
  algorithm = config.get(
    "algorithm",
    "random_forest",
  )

  if algorithm != "random_forest":
    raise ValueError(
      f"Unsupported algorithm: {algorithm}"
    )

  feature_set_id = config.get("feature_set_id")

  if feature_set_id is None:
    raise ValueError(
      "A persisted Feature Set must be selected."
    )

  target_name = config.get("target", "moa")

  (
    X,
    y,
    feature_names,
    image_ids,
    groups,
    feature_set_record,
  ) = _load_feature_set_dataset(
    dataset_id=dataset_id,
    feature_set_id=int(feature_set_id),
    target_name=target_name,
  )

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
    "feature_set_id": int(feature_set_id),
    "feature_set_name": feature_set_record["name"],
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