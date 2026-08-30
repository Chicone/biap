from collections import Counter
import json

import numpy as np
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import (
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_val_predict,
)
from db import get_connection

TARGET_FIELDS = {
    "moa": "MOA",
    "compound": "Compound",
    "concentration": "Concentration",
    "target": "Target",
}


def get_available_targets(dataset_id: int):
  """
  Return supervised-learning targets that actually contain
  useful values in the active dataset.
  """

  with get_connection() as conn:
    rows = conn.execute(
      """
      SELECT
          moa,
          compound,
          concentration,
          target
      FROM images
      WHERE dataset_id = ?
      """,
      (dataset_id,),
    ).fetchall()

  available_targets = []

  for field_name, label in TARGET_FIELDS.items():
    values = {
      row[field_name]
      for row in rows
      if row[field_name] is not None
         and row[field_name] != ""
    }

    # A supervised classification target only makes sense
    # when at least two distinct classes/values exist.
    if len(values) >= 2:
      available_targets.append(
        {
          "value": field_name,
          "label": label,
          "num_classes": len(values),
        }
      )

  return available_targets


def _load_feature_set_dataset(
    dataset_id: int,
    feature_set_id: int,
    target_name: str,
):
  allowed_targets = set(TARGET_FIELDS.keys())

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
        images.concentration,
        images.target
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

  feature_set_configuration = json.loads(
    feature_set_record["configuration_json"]
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

    aggregation_level = feature_set_configuration.get(
      "aggregation_level",
      "object",
    )

    if aggregation_level == "image":
      if len(object_features) != 1:
        raise ValueError(
          "Image-level Feature Sets must contain exactly "
          "one stored row per image."
        )

      aggregated_features = {}

      for feature_name in stored_feature_names:
        value = object_features[0].get(feature_name)

        if not isinstance(value, (int, float)):
          raise ValueError(
            f'Feature "{feature_name}" is missing or non-numeric '
            f"for image {image_id}."
          )

        numeric_value = float(value)

        if not np.isfinite(numeric_value):
          raise ValueError(
            f'Feature "{feature_name}" contains a non-finite '
            f"value for image {image_id}."
          )

        aggregated_features[feature_name] = numeric_value

    else:
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

def save_ml_run(
  dataset_id: int,
  feature_set_id: int,
  config: dict,
  result: dict,
):
  report = result["classification_report"]

  macro_f1 = report.get(
    "macro avg",
    {},
  ).get("f1-score")

  weighted_f1 = report.get(
    "weighted avg",
    {},
  ).get("f1-score")

  with get_connection() as conn:
    cursor = conn.execute(
      """
      INSERT INTO ml_runs
      (
          dataset_id,
          feature_set_id,
          target,
          algorithm,
          cv_strategy,
          cv_folds,
          random_seed,
          num_samples,
          num_features,
          num_classes,
          accuracy,
          macro_f1,
          weighted_f1,
          result_json
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (
        dataset_id,
        feature_set_id,
        config.get("target", "moa"),
        config.get("algorithm", "random_forest"),
        config.get("cv_strategy", "stratified"),
        result["cross_validation"]["folds"],
        config.get("random_seed", 42),
        result["num_samples"],
        result["num_features"],
        result["num_classes"],
        result["accuracy"],
        macro_f1,
        weighted_f1,
        json.dumps(result),
      ),
    )

    run_id = cursor.lastrowid

  return run_id

def get_ml_runs(dataset_id: int):
  with get_connection() as conn:
    rows = conn.execute(
      """
      SELECT
          ml_runs.id,
          ml_runs.dataset_id,
          ml_runs.feature_set_id,
          feature_sets.name AS feature_set_name,

          ml_runs.target,
          ml_runs.algorithm,
          ml_runs.cv_strategy,
          ml_runs.cv_folds,
          ml_runs.random_seed,

          ml_runs.num_samples,
          ml_runs.num_features,
          ml_runs.num_classes,

          ml_runs.accuracy,
          ml_runs.macro_f1,
          ml_runs.weighted_f1,

          ml_runs.created_at

      FROM ml_runs

      JOIN feature_sets
        ON feature_sets.id = ml_runs.feature_set_id

      WHERE ml_runs.dataset_id = ?

      ORDER BY ml_runs.id DESC
      """,
      (dataset_id,),
    ).fetchall()

  return [
    dict(row)
    for row in rows
  ]

def train_model(dataset_id: int, config: dict):
  algorithm = config.get(
    "algorithm",
    "random_forest",
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

  model_name = config.get("algorithm", "random_forest")

  if model_name == "random_forest":
    model = RandomForestClassifier(
      n_estimators=200,
      random_state=random_seed,
      class_weight="balanced",
      n_jobs=-1,
    )

  elif model_name == "ridge":
    model = make_pipeline(
      StandardScaler(),
      RidgeClassifier(
        class_weight="balanced",
      ),
    )

  elif model_name == "logistic_regression":
    model = make_pipeline(
      StandardScaler(),
      LogisticRegression(
        max_iter=3000,
        random_state=random_seed,
        class_weight="balanced",
      ),
    )

  elif model_name == "linear_svm":
    model = make_pipeline(
      StandardScaler(),
      LinearSVC(
        random_state=random_seed,
        class_weight="balanced",
      ),
    )

  else:
    raise ValueError(
      f"Unsupported model: {model_name}"
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

  # -------------------------------------------------------------
  # Feature importance
  # -------------------------------------------------------------
  #
  # Random Forest exposes feature_importances_ directly.
  #
  # Linear classifiers expose coefficients instead. For
  # multiclass models we use the mean absolute coefficient
  # across classes as a simple global importance measure.

  if model_name == "random_forest":
    importances = model.feature_importances_

  else:
    classifier = model[-1]

    if hasattr(classifier, "coef_"):
      coefficients = np.asarray(
        classifier.coef_,
        dtype=float,
      )

      if coefficients.ndim == 1:
        importances = np.abs(coefficients)
      else:
        importances = np.mean(
          np.abs(coefficients),
          axis=0,
        )

    else:
      importances = np.zeros(
        len(feature_names),
        dtype=float,
      )

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

  result = {
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

  run_id = save_ml_run(
    dataset_id=dataset_id,
    feature_set_id=int(feature_set_id),
    config=config,
    result=result,
  )

  result["run_id"] = run_id

  return result