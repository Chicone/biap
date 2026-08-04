import { useState } from "react";
import { Button } from "@/components/ui/button";
import FeatureMatrixTable from "@/components/experiments/feature_analysis/FeatureMatrixTable";
import FeatureSetCard from "@/components/experiments/feature_analysis/FeatureSetCard";
import FeatureBuilderSection from "@/components/experiments/feature_analysis/FeatureBuilderSection";
import FeatureScatterPlot from "@/components/experiments/feature_analysis/FeatureScatterPlot";

const API_URL = "http://127.0.0.1:8002";

function FeatureAnalysisTab({ activeDataset }) {
  const [featureSetName, setFeatureSetName] = useState("Cell Features v1");
  const [selectedSources, setSelectedSources] = useState({
    morphology: true,
    intensity: true,
    texture: true,
  });

  const [featureSet, setFeatureSet] = useState(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildError, setBuildError] = useState(null);
  const [showMatrix, setShowMatrix] = useState(false);

  const [removeConstantFeatures, setRemoveConstantFeatures] = useState(true);
  const [removeCorrelatedFeatures, setRemoveCorrelatedFeatures] = useState(false);
  const [correlationThreshold, setCorrelationThreshold] = useState(0.95);

  const [scalingMethod, setScalingMethod] = useState("none");
  const [pcaComponents, setPcaComponents] = useState(0);
  const [pcaMode, setPcaMode] = useState("add");
  const [umapComponents, setUmapComponents] = useState(0);
  const [umapMode, setUmapMode] = useState("add");

  const featureSources = [
    { key: "morphology", label: "Morphology", featureCount: 11 },
    { key: "intensity", label: "Intensity", featureCount: 6 },
    { key: "texture", label: "Texture", featureCount: 6 },
  ];

  const totalSelectedFeatures = featureSources
    .filter((source) => selectedSources[source.key])
    .reduce((total, source) => total + source.featureCount, 0);

  function handleToggleSource(sourceKey) {
    setSelectedSources((currentSources) => ({
      ...currentSources,
      [sourceKey]: !currentSources[sourceKey],
    }));
  }

  async function handleCreateFeatureSet() {
    if (!activeDataset) {
      return;
    }

    setIsBuilding(true);
    setBuildError(null);
    setFeatureSet(null);

    const response = await fetch(
      `${API_URL}/datasets/${activeDataset.id}/feature-sets`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: featureSetName.trim(),

          morphology: selectedSources.morphology,
          intensity: selectedSources.intensity,
          texture: selectedSources.texture,

          foreground: "bright",

          remove_constant: removeConstantFeatures,
          remove_correlated: removeCorrelatedFeatures,
          correlation_threshold: correlationThreshold,

          scaling: scalingMethod,

          pca_components: pcaComponents,
          pca_mode: pcaMode,

          umap_components: umapComponents,
          umap_mode: umapMode,
        }),
      }
    );

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/feature-sets`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: featureSetName.trim(),
            morphology: selectedSources.morphology,
            intensity: selectedSources.intensity,
            texture: selectedSources.texture,
            foreground: "bright",
            remove_constant: removeConstantFeatures,
            remove_correlated: removeCorrelatedFeatures,
            correlation_threshold: correlationThreshold,
            scaling: scalingMethod,
            pca_components: pcaComponents,
            pca_mode: pcaMode,
            umap_components: umapComponents,
            umap_mode: umapMode,
          }),
        }
      );

      if (!response.ok) {
        const errorResult = await response.json().catch(() => null);

        throw new Error(
          typeof errorResult?.detail === "string"
            ? errorResult.detail
            : "Feature set creation failed"
        );
      }
      const result = await response.json();

      setFeatureSet({
        ...result,
        name: featureSetName,
      });
      setShowMatrix(false);
    } catch (error) {
      setBuildError(error.message);
    } finally {
      setIsBuilding(false);
    }
  }

  if (!activeDataset) {
    return (
      <div className="workspace-content">
        <p>Select a dataset first.</p>
      </div>
    );
  }

  return (
    <div className="workspace-content">
      <div className="feature-analysis-layout">
        <section className="feature-builder-panel">
          <div className="section-label">Feature Set Builder</div>

          <label className="feature-builder-field">
            Feature set name
            <input
              value={featureSetName}
              onChange={(event) => setFeatureSetName(event.target.value)}
              placeholder="Cell Features v1"
            />
          </label>

          <FeatureBuilderSection title="Feature Sources">
            <div className="feature-source-list">
              {featureSources.map((source) => (
                <label className="feature-source-option" key={source.key}>
                  <input
                    type="checkbox"
                    checked={selectedSources[source.key]}
                    onChange={() => handleToggleSource(source.key)}
                  />

                  <div>
                    <strong>{source.label}</strong>
                    <span>{source.featureCount} features</span>
                  </div>
                </label>
              ))}
            </div>
          </FeatureBuilderSection>

          <FeatureBuilderSection title="Feature Selection">
            <div className="feature-source-list">
              <label className="feature-source-option">
                <input
                  type="checkbox"
                  checked={removeConstantFeatures}
                  onChange={() => setRemoveConstantFeatures(!removeConstantFeatures)}
                />

                <div>
                  <strong>Remove constant features</strong>
                  <span>Discard numeric columns with only one unique value</span>
                </div>
              </label>

              <label className="feature-source-option">
                <input
                  type="checkbox"
                  checked={removeCorrelatedFeatures}
                  onChange={() => setRemoveCorrelatedFeatures(!removeCorrelatedFeatures)}
                />

                <div>
                  <strong>Remove highly correlated features</strong>
                  <span>Discard redundant numeric columns above threshold</span>
                </div>
              </label>

              {removeCorrelatedFeatures && (
                <label className="feature-builder-field">
                  Correlation threshold
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={correlationThreshold}
                    onChange={(event) =>
                      setCorrelationThreshold(Number(event.target.value))
                    }
                  />
                </label>
              )}
            </div>
          </FeatureBuilderSection>

          <FeatureBuilderSection title="Feature Transformation">
            <div className="feature-source-list">
              <label className="feature-source-option">
                <input
                  type="radio"
                  name="scaling-method"
                  value="none"
                  checked={scalingMethod === "none"}
                  onChange={() => setScalingMethod("none")}
                />

                <div>
                  <strong>None</strong>
                  <span>Keep raw feature values</span>
                </div>
              </label>

              <label className="feature-source-option">
                <input
                  type="radio"
                  name="scaling-method"
                  value="standard"
                  checked={scalingMethod === "standard"}
                  onChange={() => setScalingMethod("standard")}
                />

                <div>
                  <strong>Standard scaling</strong>
                  <span>Zero mean and unit variance</span>
                </div>
              </label>

              <label className="feature-source-option">
                <input
                  type="radio"
                  name="scaling-method"
                  value="minmax"
                  checked={scalingMethod === "minmax"}
                  onChange={() => setScalingMethod("minmax")}
                />

                <div>
                  <strong>Min-Max scaling</strong>
                  <span>Scale numeric features to the 0–1 range</span>
                </div>
              </label>

              <label className="feature-source-option">
                <input
                  type="radio"
                  name="scaling-method"
                  value="robust"
                  checked={scalingMethod === "robust"}
                  onChange={() => setScalingMethod("robust")}
                />

                <div>
                  <strong>Robust scaling</strong>
                  <span>Use median and interquartile range</span>
                </div>
              </label>
            </div>
          </FeatureBuilderSection>

          <FeatureBuilderSection title="Dimensionality Reduction">
            <div className="feature-source-list">
              <label className="feature-source-option">
                <input
                  type="radio"
                  name="reduction-method"
                  value="none"
                  checked={pcaComponents === 0 && umapComponents === 0}
                  onChange={() => {
                    setPcaComponents(0);
                    setUmapComponents(0);
                  }}
                />

                <div>
                  <strong>None</strong>
                  <span>Do not compute dimensionality reduction</span>
                </div>
              </label>

              <label className="feature-source-option">
                <input
                  type="radio"
                  name="reduction-method"
                  value="pca"
                  checked={pcaComponents === 2}
                  onChange={() => {
                    setPcaComponents(2);
                    setUmapComponents(0);
                  }}
                />

                <div>
                  <strong>PCA 2D</strong>
                  <span>Compute pca_1 and pca_2</span>
                </div>
              </label>

              {pcaComponents > 0 && (
                <>
                  <label className="feature-source-option">
                    <input
                      type="radio"
                      name="pca-mode"
                      value="add"
                      checked={pcaMode === "add"}
                      onChange={() => setPcaMode("add")}
                    />

                    <div>
                      <strong>Add PCA columns</strong>
                      <span>Keep original features and append PCA columns</span>
                    </div>
                  </label>

                  <label className="feature-source-option">
                    <input
                      type="radio"
                      name="pca-mode"
                      value="replace"
                      checked={pcaMode === "replace"}
                      onChange={() => setPcaMode("replace")}
                    />

                    <div>
                      <strong>Replace features with PCA</strong>
                      <span>Use only PCA columns as reduced features</span>
                    </div>
                  </label>

                  {scalingMethod === "none" && (
                    <p className="feature-warning">
                      PCA is usually recommended after Standard scaling.
                    </p>
                  )}
                </>
              )}

              <label className="feature-source-option">
                <input
                  type="radio"
                  name="reduction-method"
                  value="umap"
                  checked={umapComponents === 2}
                  onChange={() => {
                    setUmapComponents(2);
                    setPcaComponents(0);
                  }}
                />

                <div>
                  <strong>UMAP 2D</strong>
                  <span>Compute umap_1 and umap_2</span>
                </div>
              </label>

              {umapComponents > 0 && (
                <>
                  <label className="feature-source-option">
                    <input
                      type="radio"
                      name="umap-mode"
                      value="add"
                      checked={umapMode === "add"}
                      onChange={() => setUmapMode("add")}
                    />

                    <div>
                      <strong>Add UMAP columns</strong>
                      <span>Keep original features and append UMAP columns</span>
                    </div>
                  </label>

                  <label className="feature-source-option">
                    <input
                      type="radio"
                      name="umap-mode"
                      value="replace"
                      checked={umapMode === "replace"}
                      onChange={() => setUmapMode("replace")}
                    />

                    <div>
                      <strong>Replace features with UMAP</strong>
                      <span>Use only UMAP columns as reduced features</span>
                    </div>
                  </label>

                  {scalingMethod === "none" && (
                    <p className="feature-warning">
                      UMAP usually works better after feature scaling.
                    </p>
                  )}
                </>
              )}
            </div>
          </FeatureBuilderSection>

          <Button
            onClick={handleCreateFeatureSet}
            disabled={
              isBuilding ||
              !featureSetName.trim() ||
              totalSelectedFeatures === 0
            }
          >
            {isBuilding
              ? "Creating..."
              : featureSet
                ? "Rebuild Feature Set"
                : "Create Feature Set"}
          </Button>

          {buildError && <p className="error-text">{buildError}</p>}
        </section>

        {featureSet && (
          <FeatureSetCard
            featureSet={featureSet}
            showMatrix={showMatrix}
            onToggleMatrix={() => setShowMatrix(!showMatrix)}
          />
        )}
      </div>

      {featureSet && (
        <FeatureScatterPlot features={featureSet.features} />
      )}

      {featureSet && showMatrix && (
        <FeatureMatrixTable features={featureSet.features} />
      )}
    </div>
  );
}

export default FeatureAnalysisTab;