import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

function MachineLearningTab({ activeDataset }) {
  const API_URL = "http://127.0.0.1:8002";
  const [target, setTarget] = useState("");
  const [availableTargets, setAvailableTargets] = useState([]);
  const [targetsError, setTargetsError] = useState(null);  const [algorithm, setAlgorithm] = useState("random_forest");
  const [featureSets, setFeatureSets] = useState([]);
  const [selectedFeatureSetId, setSelectedFeatureSetId] = useState("");
  const [featureSetsError, setFeatureSetsError] = useState(null);
  const [cvStrategy, setCvStrategy] = useState("stratified");
  const [cvFolds, setCvFolds] = useState(5);
  const [randomSeed, setRandomSeed] = useState(42);
  const [trainingResult, setTrainingResult] = useState(null);
  const [trainingError, setTrainingError] = useState(null);
  const [isTraining, setIsTraining] = useState(false);
  const [confusionDisplay, setConfusionDisplay] = useState("counts");
  const [selectedConfusionCell, setSelectedConfusionCell] = useState(null);
  const [selectedPredictionImage, setSelectedPredictionImage] = useState(null);
  const [comparisonA, setComparisonA] = useState(null);
  const [comparisonB, setComparisonB] = useState(null);
  const [savedRuns, setSavedRuns] = useState([]);
  const [savedRunsError, setSavedRunsError] = useState(null);
  const [selectedRunIds, setSelectedRunIds] = useState([]);
  const [runFilter, setRunFilter] = useState("");

  async function loadAvailableTargets() {
    if (!activeDataset) {
      setAvailableTargets([]);
      setTarget("");
      return;
    }

    setTargetsError(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/machine-learning/targets`
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Failed to load targets"
        );
      }

      setAvailableTargets(result);

      setTarget(
        result.length > 0
          ? result[0].value
          : ""
      );
    } catch (error) {
      setTargetsError(error.message);
      setAvailableTargets([]);
      setTarget("");
    }
  }

  async function loadFeatureSets() {
    if (!activeDataset) {
      return;
    }

    setFeatureSetsError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8002/datasets/${activeDataset.id}/feature-sets`
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Failed to load feature sets"
        );
      }

      setFeatureSets(result);

      setSelectedFeatureSetId((currentId) => {
        if (currentId) {
          return currentId;
        }

        return result.length > 0
          ? String(result[0].id)
          : "";
      });
    } catch (error) {
      setFeatureSetsError(error.message);
      setFeatureSets([]);
      setSelectedFeatureSetId("");
    }
  }

  async function loadSavedRuns() {
    if (!activeDataset) {
      setSavedRuns([]);
      return;
    }

    setSavedRunsError(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/machine-learning/runs`
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Failed to load ML runs"
        );
      }

      setSavedRuns(result);
    } catch (error) {
      setSavedRunsError(error.message);
      setSavedRuns([]);
    }
  }


  useEffect(() => {
    loadFeatureSets();
    loadAvailableTargets();
    loadSavedRuns();
  }, [activeDataset]);


  async function handleTrainModel() {
    if (!activeDataset) {
      return;
    }

    setIsTraining(true);
    setTrainingResult(null);
    setTrainingError(null);
    await loadSavedRuns();

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/machine-learning/train`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            feature_set_id: Number(selectedFeatureSetId),
            target,
            algorithm,
            cv_strategy: cvStrategy,
            cv_folds: cvFolds,
            random_seed: randomSeed,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : JSON.stringify(
                result.detail ?? result,
                null,
                2
              )
        );
      }

      setTrainingResult(result);
    } catch (error) {
      setTrainingError(error.message);
    } finally {
      setIsTraining(false);
    }
  }

  function addToComparison(item) {
    if (!comparisonA) {
      setComparisonA(item);
      return;
    }

    if (!comparisonB) {
      setComparisonB(item);
      return;
    }

    setComparisonA(item);
    setComparisonB(null);
  }

  return (
    <div className="workspace-content machine-learning-tab">
      <div className="workspace-header">
        <h3>Machine Learning</h3>
        <p>Configure supervised learning from extracted image features.</p>
      </div>

      <div className="ml-config-grid">
        <section className="ml-card">
          <h4>Target</h4>

          {targetsError && (
            <p className="ml-field-error">
              {targetsError}
            </p>
          )}

          {availableTargets.length === 0 ? (
            <p className="ml-empty-message">
              No supervised learning targets are available
              for this dataset.
            </p>
          ) : (
            <div className="ml-option-list">
              {availableTargets.map((targetOption) => (
                <label key={targetOption.value}>
                  <input
                    type="radio"
                    checked={target === targetOption.value}
                    onChange={() =>
                      setTarget(targetOption.value)
                    }
                  />

                  {targetOption.label}

                  <span>
                    {" "}
                    ({targetOption.num_classes} classes)
                  </span>
                </label>
              ))}
            </div>
          )}
        </section>

        <section className="ml-card">
          <h4>Feature Set</h4>

          {featureSetsError && (
            <p className="ml-field-error">
              {featureSetsError}
            </p>
          )}

          {featureSets.length === 0 ? (
            <p className="ml-empty-message">
              No persisted feature sets are available. Create one in
              Feature Analysis first.
            </p>
          ) : (
            <>
              <label className="ml-field">
                <span>Stored feature set</span>

                <select
                  value={selectedFeatureSetId}
                  onChange={(event) =>
                    setSelectedFeatureSetId(event.target.value)
                  }
                >
                  {featureSets.map((featureSet) => (
                    <option
                      key={featureSet.id}
                      value={featureSet.id}
                    >
                      {featureSet.name}
                    </option>
                  ))}
                </select>
              </label>

              {selectedFeatureSetId && (() => {
                const selectedFeatureSet = featureSets.find(
                  (featureSet) =>
                    String(featureSet.id) === selectedFeatureSetId
                );

                if (!selectedFeatureSet) {
                  return null;
                }

                return (
                  <div className="ml-feature-set-summary">
                    <span>
                      {selectedFeatureSet.num_rows} rows
                    </span>

                    <span>
                      {selectedFeatureSet.num_features} features
                    </span>
                  </div>
                );
              })()}
            </>
          )}
        </section>

        <section className="ml-card">
          <h4>Model</h4>

          <label className="ml-field">
            <span>Algorithm</span>
            <select
              value={algorithm}
              onChange={(event) => setAlgorithm(event.target.value)}
            >
              <option value="random_forest">Random Forest</option>
              <option value="ridge">Ridge Classifier</option>
              <option value="logistic_regression">Logistic Regression</option>
              <option value="linear_svm">Linear SVM</option>
            </select>
          </label>
        </section>

      <section className="ml-card">
        <h4>Evaluation</h4>

        <div className="ml-evaluation-fields">
          <label className="ml-field">
            <span>Cross-validation strategy</span>

            <select
              value={cvStrategy}
              onChange={(event) => setCvStrategy(event.target.value)}
            >
              <option value="stratified">
                Stratified K-Fold
              </option>

              <option value="group_well">
                Well-aware Stratified Group K-Fold
              </option>
            </select>
          </label>

          <div className="ml-field-grid">
            <label className="ml-field">
              <span>CV folds</span>
              <input
                type="number"
                min="2"
                max="50"
                value={cvFolds}
                onChange={(event) =>
                  setCvFolds(Number(event.target.value))
                }
              />
            </label>

            <label className="ml-field">
              <span>Random seed</span>
              <input
                type="number"
                value={randomSeed}
                onChange={(event) =>
                  setRandomSeed(Number(event.target.value))
                }
              />
            </label>
          </div>

          {cvStrategy === "group_well" && (
            <small className="ml-evaluation-note">
              All fields of view from the same plate and well remain
              together in one fold.
            </small>
          )}
        </div>
      </section>
      </div>

      {isTraining && (
        <p className="ml-training-status">
          Evaluating model using cross-validation...
        </p>
      )}
      <Button
        onClick={handleTrainModel}
        disabled={isTraining || !selectedFeatureSetId || !target}
      >
        {isTraining ? "Evaluating..." : "Evaluate Model"}
      </Button>
      {trainingError && (
        <section className="ml-results-card error">
          <h4>Training failed</h4>
          <p>{trainingError}</p>
        </section>
      )}

      <label className="ml-field">
        <span>Filter saved runs</span>
        <input
          type="text"
          value={runFilter}
          onChange={(event) =>
            setRunFilter(event.target.value)
          }
          placeholder="Feature set, target, algorithm, run ID..."
        />
      </label>

      <section className="ml-results-card">
        <h4>Saved Evaluation Runs</h4>

        {savedRunsError && (
          <p className="ml-field-error">
            {savedRunsError}
          </p>
        )}

        {savedRuns.length === 0 ? (
          <p className="ml-empty-message">
            No saved evaluation runs yet.
          </p>
        ) : (
          <table className="ml-results-table">
            <thead>
              <tr>
                <th></th>
                <th>Run</th>
                <th>Feature Set</th>
                <th>Target</th>
                <th>Algorithm</th>
                <th>CV</th>
                <th>Accuracy</th>
                <th>Macro F1</th>
                <th>Weighted F1</th>
              </tr>
            </thead>

            <tbody>
              {savedRuns
                .filter((run) => {
                  const query = runFilter
                    .trim()
                    .toLowerCase();

                  if (!query) {
                    return true;
                  }

                  const searchableText = [
                    run.id,
                    run.feature_set_name,
                    run.target,
                    run.algorithm,
                    run.cv_strategy,
                  ]
                    .join(" ")
                    .toLowerCase();

                  return searchableText.includes(query);
                })
                .map((run) => (
                <tr key={run.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedRunIds.includes(run.id)}
                      onChange={() => {
                        setSelectedRunIds((currentIds) =>
                          currentIds.includes(run.id)
                            ? currentIds.filter((id) => id !== run.id)
                            : [...currentIds, run.id]
                        );
                      }}
                    />
                  </td>
                  <td>#{run.id}</td>

                  <td>
                    {run.feature_set_name}
                  </td>

                  <td>
                    {run.target}
                  </td>

                  <td>
                    {run.algorithm}
                  </td>

                  <td>
                    {run.cv_folds}-fold{" "}
                    {run.cv_strategy}
                  </td>

                  <td>
                    {(run.accuracy * 100).toFixed(1)}%
                  </td>

                  <td>
                    {run.macro_f1 !== null
                      ? run.macro_f1.toFixed(3)
                      : "—"}
                  </td>

                  <td>
                    {run.weighted_f1 !== null
                      ? run.weighted_f1.toFixed(3)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {selectedRunIds.length > 0 && (
        <section className="ml-results-card">
          <h4>Selected Run Comparison</h4>

          <table className="ml-results-table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Feature Set</th>
                <th>Target</th>
                <th>Algorithm</th>
                <th>CV</th>
                <th>Samples</th>
                <th>Features</th>
                <th>Accuracy</th>
                <th>Macro F1</th>
                <th>Weighted F1</th>
              </tr>
            </thead>

            <tbody>
              {savedRuns
                .filter((run) =>
                  selectedRunIds.includes(run.id)
                )
                .map((run) => (
                  <tr key={run.id}>
                    <td>#{run.id}</td>

                    <td>
                      {run.feature_set_name}
                    </td>

                    <td>
                      {run.target}
                    </td>

                    <td>
                      {run.algorithm}
                    </td>

                    <td>
                      {run.cv_folds}-fold{" "}
                      {run.cv_strategy}
                    </td>

                    <td>
                      {run.num_samples}
                    </td>

                    <td>
                      {run.num_features}
                    </td>

                    <td>
                      {(run.accuracy * 100).toFixed(1)}%
                    </td>

                    <td>
                      {run.macro_f1 !== null
                        ? run.macro_f1.toFixed(3)
                        : "—"}
                    </td>

                    <td>
                      {run.weighted_f1 !== null
                        ? run.weighted_f1.toFixed(3)
                        : "—"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </section>
      )}

      {trainingResult && (
        <section className="ml-results-card">
          <h4>Cross-Validation Results</h4>

          <div className="ml-results-grid">
            <div>
              <span>Feature Set</span>
              <strong>
                {trainingResult.feature_set_name}
              </strong>
            </div>

            <div>
              <span>Samples</span>
              <strong>{trainingResult.num_samples}</strong>
            </div>

            <div>
              <span>Features</span>
              <strong>{trainingResult.num_features}</strong>
            </div>

            <div>
              <span>Classes</span>
              <strong>{trainingResult.num_classes}</strong>
            </div>

            <div>
              <span>Accuracy</span>
              <strong>
                {(trainingResult.accuracy * 100).toFixed(1)}%
              </strong>
            </div>

            <div>
              <span>Evaluation</span>
              <strong>
                {trainingResult.cross_validation.strategy === "group_well"
                  ? `${trainingResult.cross_validation.folds}-Fold Well-Aware CV`
                  : `${trainingResult.cross_validation.folds}-Fold Stratified CV`}
              </strong>
            </div>
            {trainingResult.cross_validation.num_groups !== null && (
              <div>
                <span>Wells</span>
                <strong>
                  {trainingResult.cross_validation.num_groups}
                </strong>
              </div>
            )}
          </div>

          <h5>Confusion Matrix</h5>

          <div className="ml-confusion-toolbar">
            <Button
              variant={confusionDisplay === "counts" ? "default" : "outline"}
              size="sm"
              onClick={() => setConfusionDisplay("counts")}
            >
              Counts
            </Button>

            <Button
              variant={confusionDisplay === "normalized" ? "default" : "outline"}
              size="sm"
              onClick={() => setConfusionDisplay("normalized")}
            >
              Row-normalized (%)
            </Button>
          </div>

          <table className="ml-confusion-matrix">
            <thead>
              <tr>
                <th></th>
                {trainingResult.labels.map((label) => (
                  <th key={label}>{label}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {trainingResult.confusion_matrix.map((row, rowIndex) => (
                <tr key={trainingResult.labels[rowIndex]}>
                  <th>{trainingResult.labels[rowIndex]}</th>

                  {(() => {
                    const rowTotal = row.reduce((a, b) => a + b, 0);

                    return row.map((value, colIndex) => (
                      <td
                        key={`${rowIndex}-${colIndex}`}
                        className="ml-confusion-cell"
                        onClick={() => {
                          setSelectedConfusionCell({
                            actual: trainingResult.labels[rowIndex],
                            predicted: trainingResult.labels[colIndex],
                          });
                          setSelectedPredictionImage(null);
                        }}
                      >
                        {confusionDisplay === "normalized"
                          ? `${((100 * value) / rowTotal).toFixed(1)}%`
                          : value}
                      </td>
                    ));
                  })()}
                </tr>
              ))}
            </tbody>
          </table>

          {selectedConfusionCell && (
            <section className="ml-confusion-detail">
              <h5>
                Images: {selectedConfusionCell.actual} →{" "}
                {selectedConfusionCell.predicted}
              </h5>

              {(comparisonA || comparisonB) && (
                <section className="ml-comparison-panel">
                  <div className="ml-comparison-header">
                    <h5>Image Comparison</h5>

                    <button
                      type="button"
                      className="ml-clear-comparison-button"
                      onClick={() => {
                        setComparisonA(null);
                        setComparisonB(null);
                      }}
                    >
                      Clear
                    </button>
                  </div>

                  <div className="ml-comparison-grid">
                    <div className="ml-comparison-slot">
                      <h6>Image A</h6>

                      {comparisonA ? (
                        <>
                          <p>
                            ID {comparisonA.image_id} · Actual: {comparisonA.actual} ·
                            Predicted: {comparisonA.predicted}
                          </p>

                          <img
                            src={`http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${comparisonA.image_id}/preview`}
                            alt={`Image ${comparisonA.image_id}`}
                            className="ml-comparison-image"
                          />
                        </>
                      ) : (
                        <p>Select an image to compare.</p>
                      )}
                    </div>

                    <div className="ml-comparison-slot">
                      <h6>Image B</h6>

                      {comparisonB ? (
                        <>
                          <p>
                            ID {comparisonB.image_id} · Actual: {comparisonB.actual} ·
                            Predicted: {comparisonB.predicted}
                          </p>

                          <img
                            src={`http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${comparisonB.image_id}/preview`}
                            alt={`Image ${comparisonB.image_id}`}
                            className="ml-comparison-image"
                          />
                        </>
                      ) : (
                        <p>Select a second image to compare.</p>
                      )}
                    </div>
                  </div>
                </section>
              )}

              {trainingResult.predictions.filter(
                (item) =>
                  item.actual === selectedConfusionCell.actual &&
                  item.predicted === selectedConfusionCell.predicted
              ).length === 0 ? (
                <p>No images in this cell.</p>
              ) : (
                <table className="ml-results-table">
                  <thead>
                    <tr>
                      <th>Image</th>
                      <th>Image ID</th>
                      <th>Actual</th>
                      <th>Predicted</th>
                    </tr>
                  </thead>

                  <tbody>
                    {trainingResult.predictions
                      .filter(
                        (item) =>
                          item.actual === selectedConfusionCell.actual &&
                          item.predicted === selectedConfusionCell.predicted
                      )
                      .map((item) => (
                        <tr key={item.image_id}>
                          <td>
                            <div className="ml-thumbnail-actions">
                              <button
                                type="button"
                                className="ml-thumbnail-button"
                                onClick={() => setSelectedPredictionImage(item)}
                              >
                                <img
                                  src={`http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${item.image_id}/preview`}
                                  alt={`Image ${item.image_id}`}
                                  className="ml-misclassified-thumbnail"
                                />
                              </button>

                              <button
                                type="button"
                                className="ml-compare-button"
                                onClick={() => addToComparison(item)}
                              >
                                Compare
                              </button>
                            </div>
                          </td>
                          <td>{item.image_id}</td>
                          <td>{item.actual}</td>
                          <td>{item.predicted}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              )}

            {selectedPredictionImage && (
              <div className="ml-selected-prediction-preview">
                <div>
                  <h5>Image {selectedPredictionImage.image_id}</h5>
                  <p>
                    Actual: {selectedPredictionImage.actual} · Predicted:{" "}
                    {selectedPredictionImage.predicted}
                  </p>
                </div>

                <img
                  src={`http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${selectedPredictionImage.image_id}/preview`}
                  alt={`Image ${selectedPredictionImage.image_id}`}
                  className="ml-selected-prediction-image"
                />
              </div>
            )}


            </section>
          )}

          <h5>Classification Report</h5>
            <table className="ml-results-table">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1-score</th>
                  <th>Support</th>
                </tr>
              </thead>

              <tbody>
                {trainingResult.labels.map((label) => {
                  const row = trainingResult.classification_report[label];

                  return (
                    <tr key={label}>
                      <td>{label}</td>
                      <td>{row.precision.toFixed(3)}</td>
                      <td>{row.recall.toFixed(3)}</td>
                      <td>{row["f1-score"].toFixed(3)}</td>
                      <td>{row.support}</td>
                    </tr>
                  );
                })}

                <tr>
                  <td><strong>Macro avg</strong></td>
                  <td>
                    {trainingResult.classification_report["macro avg"].precision.toFixed(3)}
                  </td>
                  <td>
                    {trainingResult.classification_report["macro avg"].recall.toFixed(3)}
                  </td>
                  <td>
                    {trainingResult.classification_report["macro avg"]["f1-score"].toFixed(3)}
                  </td>
                  <td>
                    {trainingResult.classification_report["macro avg"].support}
                  </td>
                </tr>

                <tr>
                  <td><strong>Weighted avg</strong></td>
                  <td>
                    {trainingResult.classification_report["weighted avg"].precision.toFixed(3)}
                  </td>
                  <td>
                    {trainingResult.classification_report["weighted avg"].recall.toFixed(3)}
                  </td>
                  <td>
                    {trainingResult.classification_report["weighted avg"]["f1-score"].toFixed(3)}
                  </td>
                  <td>
                    {trainingResult.classification_report["weighted avg"].support}
                  </td>
                </tr>
              </tbody>
            </table>

          <h5>Top Features</h5>

          <table className="ml-results-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Importance</th>
              </tr>
            </thead>
            <tbody>
              {trainingResult.top_features.slice(0, 10).map((feature) => (
                <tr key={feature.feature}>
                  <td>{feature.feature}</td>
                  <td>{feature.importance.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

export default MachineLearningTab;