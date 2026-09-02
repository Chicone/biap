from collections import Counter
import json

import numpy as np
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
)
from scipy.stats import spearmanr
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
  Return supervised-learning targets available for the active dataset.

  Image datasets:
      categorical targets from the images table.

  Antibody datasets:
      numeric regression targets discovered dynamically from targets_json.
  """

  with get_connection() as conn:
    dataset_row = conn.execute(
      """
      SELECT dataset_type
      FROM datasets
      WHERE id = ?
      """,
      (dataset_id,),
    ).fetchone()

    if dataset_row is None:
      raise ValueError(
        f"Dataset {dataset_id} was not found."
      )

    dataset_type = (
      dataset_row["dataset_type"]
      .strip()
      .lower()
    )

    if dataset_type == "antibody":
      rows = conn.execute(
        """
        SELECT targets_json
        FROM antibody_samples
        WHERE dataset_id = ?
        """,
        (dataset_id,),
      ).fetchall()

      values_by_target = {}

      for row in rows:
        targets_json = row["targets_json"]

        if not targets_json:
          continue

        targets = json.loads(targets_json)

        for target_name, value in targets.items():
          if not isinstance(value, (int, float)):
            continue

          if not np.isfinite(float(value)):
            continue

          values_by_target.setdefault(
            target_name,
            [],
          ).append(float(value))

      available_targets = []

      for target_name in sorted(values_by_target):
        values = values_by_target[target_name]

        if len(values) < 2:
          continue

        available_targets.append(
          {
            "value": target_name,
            "label": target_name,
            "task_type": "regression",
            "num_samples": len(values),
          }
        )

      return available_targets

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

    if len(values) >= 2:
      available_targets.append(
        {
          "value": field_name,
          "label": label,
          "task_type": "classification",
          "num_classes": len(values),
        }
      )

  return available_targets


def _load_image_feature_set_dataset(
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
        "compound": record.get("compound"),
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
  compound_groups = []

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
    compound_groups.append(image_entry.get("compound"))

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
    np.array(compound_groups, dtype=object),
    feature_set_record,
  )

def _load_antibody_feature_set_dataset(
  dataset_id: int,
  feature_set_id: int,
  target_name: str,
  competition_mode: bool = False,
):
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
          antibody_feature_set_rows.antibody_sample_id,
          antibody_feature_set_rows.features_json,
          antibody_samples.sample_name,
          antibody_samples.metadata_json,
          antibody_samples.targets_json
      FROM antibody_feature_set_rows
      JOIN antibody_samples
        ON antibody_samples.id =
           antibody_feature_set_rows.antibody_sample_id
      WHERE antibody_feature_set_rows.feature_set_id = ?
      ORDER BY antibody_feature_set_rows.antibody_sample_id
      """,
      (feature_set_id,),
    ).fetchall()

  if not stored_rows:
    raise ValueError(
      "The selected antibody Feature Set contains no stored rows."
    )

  stored_feature_names = json.loads(
    feature_set_record["feature_names_json"]
  )

  if not stored_feature_names:
    raise ValueError(
      "The selected Feature Set contains no features."
    )

  feature_rows = []
  targets = []
  sample_ids = []
  competition_folds = []

  for row in stored_rows:
    record = dict(row)

    if competition_mode:
      metadata = json.loads(
        record.get("metadata_json") or "{}"
      )

      competition_targets = metadata.get(
        "competition_targets",
        [],
      )

      if target_name not in competition_targets:
        continue

    targets_json = record.get("targets_json")

    if not targets_json:
      continue

    sample_targets = json.loads(targets_json)

    target_value = sample_targets.get(target_name)

    if not isinstance(target_value, (int, float)):
      continue

    target_value = float(target_value)

    if not np.isfinite(target_value):
      continue

    features = json.loads(
      record["features_json"]
    )

    numeric_features = {}

    for feature_name in stored_feature_names:
      value = features.get(feature_name)

      if not isinstance(value, (int, float)):
        raise ValueError(
          f'Feature "{feature_name}" is missing or '
          f'non-numeric for antibody sample '
          f'{record["antibody_sample_id"]}.'
        )

      numeric_value = float(value)

      if not np.isfinite(numeric_value):
        raise ValueError(
          f'Feature "{feature_name}" contains a '
          f'non-finite value for antibody sample '
          f'{record["antibody_sample_id"]}.'
        )

      numeric_features[feature_name] = numeric_value

    feature_rows.append(numeric_features)
    targets.append(target_value)
    sample_ids.append(
      int(record["antibody_sample_id"])
    )

    metadata_json = record.get("metadata_json")
    metadata = json.loads(metadata_json or "{}")

    competition_folds.append(
      metadata.get("competition_fold")
    )

  if not feature_rows:
    raise ValueError(
      f'No antibody samples contain a valid "{target_name}" '
      "target and Feature Set row."
    )

  matrix = np.array(
    [
      [
        feature_row[feature_name]
        for feature_name in stored_feature_names
      ]
      for feature_row in feature_rows
    ],
    dtype=float,
  )

  return (
    matrix,
    np.array(targets, dtype=float),
    stored_feature_names,
    sample_ids,
    np.array(
      [None] * len(sample_ids),
      dtype=object,
    ),
    np.array(
      [None] * len(sample_ids),
      dtype=object,
    ),
    np.array(
      competition_folds,
      dtype=object,
    ),
    feature_set_record,
  )

def _load_feature_set_dataset(
  dataset_id: int,
  feature_set_id: int,
  target_name: str,
  competition_mode: bool = False,
):
  with get_connection() as conn:
    dataset_row = conn.execute(
      """
      SELECT dataset_type
      FROM datasets
      WHERE id = ?
      """,
      (dataset_id,),
    ).fetchone()

  if dataset_row is None:
    raise ValueError(
      f"Dataset {dataset_id} was not found."
    )

  dataset_type = (
    dataset_row["dataset_type"]
    .strip()
    .lower()
  )

  if dataset_type == "antibody":
    return _load_antibody_feature_set_dataset(
      dataset_id=dataset_id,
      feature_set_id=feature_set_id,
      target_name=target_name,
      competition_mode=competition_mode,
    )

  return _load_image_feature_set_dataset(
    dataset_id=dataset_id,
    feature_set_id=feature_set_id,
    target_name=target_name,
  )

def save_ml_run(
  dataset_id: int,
  feature_set_id: int,
  config: dict,
  result: dict,
):
  task_type = result.get(
    "task_type",
    "classification",
  )

  if task_type == "classification":
    report = result["classification_report"]

    macro_f1 = report.get(
      "macro avg",
      {},
    ).get("f1-score")

    weighted_f1 = report.get(
      "weighted avg",
      {},
    ).get("f1-score")

    num_classes = result["num_classes"]
    accuracy = result["accuracy"]

    spearman = None
    mae = None
    r2 = None

  elif task_type == "regression":
    macro_f1 = None
    weighted_f1 = None

    num_classes = 0
    accuracy = 0.0

    spearman = result.get("spearman")
    mae = result.get("mae")
    r2 = result.get("r2")

  else:
    raise ValueError(
      f"Unsupported task type: {task_type}"
    )

  with get_connection() as conn:
    existing_run = conn.execute(
      """
      SELECT id
      FROM ml_runs
      WHERE dataset_id = ?
        AND feature_set_id = ?
        AND target = ?
        AND algorithm = ?
        AND cv_strategy = ?
        AND cv_folds = ?
        AND random_seed = ?
      ORDER BY id DESC
      LIMIT 1
      """,
      (
        dataset_id,
        feature_set_id,
        config.get("target", "moa"),
        config.get("algorithm", "random_forest"),
        result["cross_validation"]["strategy"],
        result["cross_validation"]["folds"],
        config.get("random_seed", 42),
      ),
    ).fetchone()

    if existing_run is not None:
      return existing_run["id"]

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
          task_type,
          spearman,
          mae,
          r2,
          result_json
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (
        dataset_id,
        feature_set_id,
        config.get("target", "moa"),
        config.get("algorithm", "random_forest"),
        result["cross_validation"]["strategy"],
        result["cross_validation"]["folds"],
        config.get("random_seed", 42),
        result["num_samples"],
        result["num_features"],
        num_classes,
        accuracy,
        macro_f1,
        weighted_f1,
        task_type,
        spearman,
        mae,
        r2,
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
          
          ml_runs.task_type,
          ml_runs.spearman,
          ml_runs.mae,
          ml_runs.r2,
          
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

def delete_ml_run(
  dataset_id: int,
  run_id: int,
):
  with get_connection() as conn:
    run = conn.execute(
      """
      SELECT id
      FROM ml_runs
      WHERE id = ?
        AND dataset_id = ?
      """,
      (run_id, dataset_id),
    ).fetchone()

    if run is None:
      raise ValueError(
        f"ML run {run_id} was not found "
        f"for dataset {dataset_id}."
      )

    conn.execute(
      """
      DELETE FROM ml_runs
      WHERE id = ?
        AND dataset_id = ?
      """,
      (run_id, dataset_id),
    )

  return {
    "status": "deleted",
    "run_id": run_id,
  }

def train_model(
  dataset_id: int,
  config: dict,
):
  with get_connection() as conn:
    dataset_row = conn.execute(
      """
      SELECT dataset_type
      FROM datasets
      WHERE id = ?
      """,
      (dataset_id,),
    ).fetchone()

  if dataset_row is None:
    raise ValueError(
      f"Dataset {dataset_id} was not found."
    )

  dataset_type = (
    dataset_row["dataset_type"]
    .strip()
    .lower()
  )

  if dataset_type == "antibody":
    return _train_regression_model(
      dataset_id=dataset_id,
      config=config,
    )

  return _train_classification_model(
    dataset_id=dataset_id,
    config=config,
  )


def _train_regression_model(
  dataset_id: int,
  config: dict,
):
  feature_set_id = config.get("feature_set_id")

  if feature_set_id is None:
    raise ValueError(
      "A persisted Feature Set must be selected."
    )

  target_name = config.get("target")

  if not target_name:
    raise ValueError(
      "A regression target must be selected."
    )

  (
    X,
    y,
    feature_names,
    sample_ids,
    _groups,
    _compound_groups,
    competition_folds,
    feature_set_record,
  ) = _load_feature_set_dataset(
    dataset_id=dataset_id,
    feature_set_id=int(feature_set_id),
    target_name=target_name,
    competition_mode=(
      config.get("cv_strategy") == "competition_fold"
    ),
  )

  if len(y) < 3:
    raise ValueError(
      "Regression evaluation requires at least "
      "three samples."
    )

  random_seed = config.get(
    "random_seed",
    42,
  )

  requested_cv_folds = config.get(
    "cv_folds",
    5,
  )

  usable_cv_folds = min(
    requested_cv_folds,
    len(y),
  )

  if usable_cv_folds < 2:
    raise ValueError(
      "Regression cross-validation requires "
      "at least two folds."
    )

  model_name = config.get(
    "algorithm",
    "random_forest",
  )

  if model_name == "random_forest":
    model = RandomForestRegressor(
      n_estimators=200,
      random_state=random_seed,
      n_jobs=-1,
    )

  elif model_name == "ridge":
    model = make_pipeline(
      StandardScaler(),
      Ridge(),
    )

  else:
    raise ValueError(
      "Antibody regression currently supports "
      "Random Forest and Ridge."
    )

  cv_strategy = config.get(
    "cv_strategy",
    "kfold",
  )

  fold_spearman = None

  if cv_strategy == "competition_fold":
    if any(
      fold is None
      for fold in competition_folds
    ):
      raise ValueError(
        "Competition-fold evaluation requires "
        "a fold assignment for every antibody."
      )

    unique_folds = sorted(
      set(
        int(fold)
        for fold in competition_folds
      )
    )

    y_pred = np.empty(
      len(y),
      dtype=float,
    )

    fold_spearman = []

    for fold in unique_folds:
      train_indices = np.array(
        [
          index
          for index, sample_fold
          in enumerate(competition_folds)
          if int(sample_fold) != fold
        ]
      )

      test_indices = np.array(
        [
          index
          for index, sample_fold
          in enumerate(competition_folds)
          if int(sample_fold) == fold
        ]
      )

      model.fit(
        X[train_indices],
        y[train_indices],
      )

      fold_predictions = model.predict(
        X[test_indices]
      )

      y_pred[test_indices] = fold_predictions

      fold_result = spearmanr(
        y[test_indices],
        fold_predictions,
      )

      fold_spearman.append(
        float(fold_result.statistic)
      )

    spearman = float(
      np.mean(fold_spearman)
    )

    usable_cv_folds = len(unique_folds)

    evaluation_name = (
      "GDPa1 competition 5-fold"
    )

  elif cv_strategy == "kfold":
    cv = KFold(
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

    spearman_result = spearmanr(
      y,
      y_pred,
    )

    spearman = float(
      spearman_result.statistic
    )

    evaluation_name = (
      f"{usable_cv_folds}-fold "
      "K-fold cross-validation"
    )

  else:
    raise ValueError(
      f"Unsupported regression CV strategy: {cv_strategy}"
    )

  mae = float(
    mean_absolute_error(
      y,
      y_pred,
    )
  )

  r2 = float(
    r2_score(
      y,
      y_pred,
    )
  )

  model.fit(
    X,
    y,
  )

  if model_name == "random_forest":
    importances = model.feature_importances_

  else:
    regressor = model[-1]

    if hasattr(regressor, "coef_"):
      importances = np.abs(
        np.asarray(
          regressor.coef_,
          dtype=float,
        )
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
      for feature_name, importance
      in zip(
        feature_names,
        importances,
      )
    ],
    key=lambda item: item["importance"],
    reverse=True,
  )

  predictions = [
    {
      "sample_id": int(sample_id),
      "actual": float(actual),
      "predicted": float(predicted),
      "residual": float(
        actual - predicted
      ),
    }
    for sample_id, actual, predicted
    in zip(
      sample_ids,
      y,
      y_pred,
    )
  ]

  result = {
    "dataset_id": dataset_id,
    "feature_set_id": int(feature_set_id),
    "feature_set_name": feature_set_record["name"],
    "status": "evaluated",
    "task_type": "regression",
    "algorithm": model_name,
    "target": target_name,
    "num_samples": int(X.shape[0]),
    "num_features": int(X.shape[1]),
    "spearman": spearman,
    "mae": mae,
    "r2": r2,
    "fold_spearman": fold_spearman,
    "cross_validation": {
      "strategy": cv_strategy,
      "name": evaluation_name,
      "folds": int(usable_cv_folds),
    },
    "predictions": predictions,
    "top_features": feature_importance[:20],
    "sample_ids": sample_ids,
  }

  run_id = save_ml_run(
    dataset_id=dataset_id,
    feature_set_id=int(feature_set_id),
    config=config,
    result=result,
  )

  result["run_id"] = run_id

  return result

def _train_classification_model(
    dataset_id: int,
    config: dict,
  ):
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
    compound_groups,
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


  elif cv_strategy == "group_compound":
    missing_group_indices = [
      index
      for index, group in enumerate(compound_groups)
      if group is None or group == ""
    ]

    if missing_group_indices:
      raise ValueError(
        "Compound-aware cross-validation requires compound "
        "metadata for every evaluated image."
      )

    unique_groups = np.unique(compound_groups)

    if len(unique_groups) < 2:
      raise ValueError(
        "Compound-aware cross-validation requires at least "
        "two distinct compounds."
      )

    groups_per_class = {}

    for class_name in labels:
      class_groups = np.unique(
        np.array(compound_groups)[y == class_name]
      )
      groups_per_class[class_name] = len(class_groups)

    min_groups_per_class = min(
      groups_per_class.values()
    )

    usable_cv_folds = min(
      requested_cv_folds,
      len(unique_groups),
      min_groups_per_class,
    )

    if usable_cv_folds < 2:
      raise ValueError(
        "Each class must contain at least two distinct "
        "compounds for compound-aware cross-validation."
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
      groups=compound_groups,
      n_jobs=-1,
    )

    evaluation_name = (
      f"{usable_cv_folds}-fold stratified group "
      "cross-validation by compound"
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