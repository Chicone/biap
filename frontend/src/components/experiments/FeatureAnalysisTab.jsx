import { useEffect, useState } from "react";
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
  const [savedFeatureSets, setSavedFeatureSets] = useState([]);
  const [savedFeatureSetsError, setSavedFeatureSetsError] = useState(null);
  const [isDeletingFeatureSet, setIsDeletingFeatureSet] = useState(false);

  const [foundationFeatureSetName, setFoundationFeatureSetName] = useState("DINOv2 Embeddings v1");
  const [handcraftedChannel, setHandcraftedChannel] = useState("");
  const [foundationChannel, setFoundationChannel] = useState("");
  const [availableChannels, setAvailableChannels] = useState([]);
  const [isGeneratingFoundationFeatures, setIsGeneratingFoundationFeatures] = useState(false);
  const [foundationFeaturesError, setFoundationFeaturesError] = useState(null);
  const [foundationFeaturesResult, setFoundationFeaturesResult] = useState(null);

  const [selectedFeatureSetIds, setSelectedFeatureSetIds] =  useState([]);
  const [combinedFeatureSetName, setCombinedFeatureSetName] = useState("Handcrafted + DINOv2");
  const [isCombiningFeatureSets, setIsCombiningFeatureSets] = useState(false);
  const [combineFeatureSetsError, setCombineFeatureSetsError] = useState(null);
  const [combineFeatureSetsResult, setCombineFeatureSetsResult] = useState(null);

  const [removeConstantFeatures, setRemoveConstantFeatures] = useState(true);
  const [removeCorrelatedFeatures, setRemoveCorrelatedFeatures] = useState(false);
  const [correlationThreshold, setCorrelationThreshold] = useState(0.95);

  const [scalingMethod, setScalingMethod] = useState("robust");
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

  const isAntibodyDataset =
  activeDataset?.dataset_type?.toLowerCase() === "antibody";
  const [antibodyFeatureSetName, setAntibodyFeatureSetName] =
  useState("Antibody Sequence Baseline");
  const [isGeneratingAntibodyFeatures, setIsGeneratingAntibodyFeatures] =
    useState(false);
  const [antibodyFeaturesError, setAntibodyFeaturesError] =
    useState(null);
  const [antibodyFeaturesResult, setAntibodyFeaturesResult] =
    useState(null);
  const [esmFeatureSetName, setEsmFeatureSetName] =
  useState("ESM-2 650M VH+VL Embeddings");

  const [isGeneratingEsmFeatures, setIsGeneratingEsmFeatures] =
    useState(false);

  const [esmFeaturesError, setEsmFeaturesError] =
    useState(null);

  const [esmFeaturesResult, setEsmFeaturesResult] =
    useState(null);

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
            channel: handcraftedChannel.trim() || null,
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
      await loadSavedFeatureSets();
    } catch (error) {
      setBuildError(error.message);
    } finally {
      setIsBuilding(false);
    }
  }

  async function loadSavedFeatureSets() {
    if (!activeDataset) {
      setSavedFeatureSets([]);
      return;
    }

    setSavedFeatureSetsError(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/feature-sets`
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Failed to load saved feature sets"
        );
      }

      setSavedFeatureSets(result);
    } catch (error) {
      setSavedFeatureSetsError(error.message);
      setSavedFeatureSets([]);
    }
  }

  async function loadAvailableChannels() {
    if (!activeDataset) {
      setAvailableChannels([]);
      setFoundationChannel("");
      setHandcraftedChannel("");
      return;
    }

    try {
      const imagesResponse = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/images`
      );

      if (!imagesResponse.ok) {
        throw new Error("Failed to load dataset images");
      }

      const images = await imagesResponse.json();

      if (images.length === 0) {
        setAvailableChannels([]);
        setFoundationChannel("");
        setHandcraftedChannel("");

        return;
      }

      const firstImageId = images[0].id;

      const channelsResponse = await fetch(
        `${API_URL}/images/${firstImageId}/channels`
      );

      if (!channelsResponse.ok) {
        throw new Error("Failed to load image channels");
      }

      const channels = await channelsResponse.json();

      const channelNames = channels.map(
        (channel) => channel.channel_name
      );

      setAvailableChannels(channelNames);

      setFoundationChannel(
        channelNames.length > 0
          ? channelNames[0]
          : ""
      );
      setHandcraftedChannel(
        channelNames.length > 0
          ? channelNames[0]
          : ""
      );
    } catch (error) {
      console.error(
        "Failed to load available channels:",
        error
      );

      setAvailableChannels([]);
      setFoundationChannel("");
      setHandcraftedChannel("");
    }
  }

  useEffect(() => {
    loadSavedFeatureSets();
    loadAvailableChannels();
  }, [activeDataset]);

  async function handleGenerateDINOv2FeatureSet() {
    if (!activeDataset || !foundationFeatureSetName.trim()) {
      return;
    }

    setIsGeneratingFoundationFeatures(true);
    setFoundationFeaturesError(null);
    setFoundationFeaturesResult(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/feature-sets/dinov2`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: foundationFeatureSetName.trim(),
            channel: foundationChannel.trim() || null,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "DINOv2 feature generation failed"
        );
      }

      setFoundationFeaturesResult(result);
      await loadSavedFeatureSets();
    } catch (error) {
      setFoundationFeaturesError(error.message);
    } finally {
      setIsGeneratingFoundationFeatures(false);
    }
  }

  async function handleGenerateAntibodyFeatureSet() {
    if (!activeDataset || !antibodyFeatureSetName.trim()) {
      return;
    }

    setIsGeneratingAntibodyFeatures(true);
    setAntibodyFeaturesError(null);
    setAntibodyFeaturesResult(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/feature-sets/antibody-sequence`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: antibodyFeatureSetName.trim(),
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Antibody feature generation failed"
        );
      }

      setAntibodyFeaturesResult(result);

      await loadSavedFeatureSets();
    } catch (error) {
      setAntibodyFeaturesError(error.message);
    } finally {
      setIsGeneratingAntibodyFeatures(false);
    }
  }

  async function handleGenerateEsmFeatureSet() {
    if (!activeDataset || !esmFeatureSetName.trim()) {
      return;
    }

    setIsGeneratingEsmFeatures(true);
    setEsmFeaturesError(null);
    setEsmFeaturesResult(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/feature-sets/antibody-esm`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: esmFeatureSetName.trim(),
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "ESM feature generation failed"
        );
      }

      setEsmFeaturesResult(result);

      await loadSavedFeatureSets();
    } catch (error) {
      setEsmFeaturesError(error.message);
    } finally {
      setIsGeneratingEsmFeatures(false);
    }
  }

  function handleToggleFeatureSet(featureSetId) {
    setSelectedFeatureSetIds((currentIds) => {
      if (currentIds.includes(featureSetId)) {
        return currentIds.filter(
          (id) => id !== featureSetId
        );
      }

      return [
        ...currentIds,
        featureSetId,
      ];
    });
  }

  async function handleCombineFeatureSets() {
    if (
      !activeDataset ||
      selectedFeatureSetIds.length < 2 ||
      !combinedFeatureSetName.trim()
    ) {
      return;
    }

    setIsCombiningFeatureSets(true);
    setCombineFeatureSetsError(null);
    setCombineFeatureSetsResult(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/feature-sets/combine`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: combinedFeatureSetName.trim(),
            feature_set_ids: selectedFeatureSetIds,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Feature Set combination failed"
        );
      }

      setCombineFeatureSetsResult(result);
      setSelectedFeatureSetIds([]);

      await loadSavedFeatureSets();
    } catch (error) {
      setCombineFeatureSetsError(error.message);
    } finally {
      setIsCombiningFeatureSets(false);
    }
  }

  async function handleDeleteFeatureSet(featureSetToDelete) {
    const confirmed = window.confirm(
      `Delete feature set "${featureSetToDelete.name}"?`
    );

    if (!confirmed) {
      return;
    }

    setIsDeletingFeatureSet(true);
    setSavedFeatureSetsError(null);

    try {
      const response = await fetch(
        `${API_URL}/feature-sets/${featureSetToDelete.id}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Failed to delete feature set"
        );
      }

      if (featureSet?.feature_set_id === featureSetToDelete.id) {
        setFeatureSet(null);
        setShowMatrix(false);
      }

      await loadSavedFeatureSets();
    } catch (error) {
      setSavedFeatureSetsError(error.message);
    } finally {
      setIsDeletingFeatureSet(false);
    }
  }

  if (!activeDataset) {
    return (
      <div className="workspace-content">
        <p>Select a dataset first.</p>
      </div>
    );
  }

  const selectedFeatureSets = savedFeatureSets.filter(
    (featureSet) =>
      selectedFeatureSetIds.includes(featureSet.id)
  );

  const selectedFeatureCount = selectedFeatureSets.reduce(
    (total, featureSet) =>
      total + featureSet.num_features,
    0
  );

  return (
    <div className="workspace-content">
      <div className="feature-analysis-layout">
        {!isAntibodyDataset && (
          <>
            <section className="feature-builder-panel feature-panel-handcrafted">
              <div className="section-label">
                Feature Set Builder
              </div>

              <label className="feature-builder-field">
                Feature set name

                <input
                  value={featureSetName}
                  onChange={(event) =>
                    setFeatureSetName(event.target.value)
                  }
                  placeholder="Cell Features v1"
                />
              </label>

              <label className="feature-builder-field">
                Image channel

                <select
                  value={handcraftedChannel}
                  onChange={(event) =>
                    setHandcraftedChannel(event.target.value)
                  }
                  disabled={
                    isBuilding ||
                    availableChannels.length === 0
                  }
                >
                  {availableChannels.length === 0 ? (
                    <option value="">
                      No channels available
                    </option>
                  ) : (
                    availableChannels.map((channelName) => (
                      <option
                        key={channelName}
                        value={channelName}
                      >
                        {channelName}
                      </option>
                    ))
                  )}
                </select>
              </label>

              <FeatureBuilderSection title="Feature Sources">
                <div className="feature-source-list">
                  {featureSources.map((source) => (
                    <label
                      className="feature-source-option"
                      key={source.key}
                    >
                      <input
                        type="checkbox"
                        checked={selectedSources[source.key]}
                        onChange={() =>
                          handleToggleSource(source.key)
                        }
                      />

                      <div>
                        <strong>{source.label}</strong>
                        <span>
                          {source.featureCount} features
                        </span>
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
                      onChange={() =>
                        setRemoveConstantFeatures(
                          !removeConstantFeatures
                        )
                      }
                    />

                    <div>
                      <strong>
                        Remove constant features
                      </strong>

                      <span>
                        Discard numeric columns with only one
                        unique value
                      </span>
                    </div>
                  </label>

                  <label className="feature-source-option">
                    <input
                      type="checkbox"
                      checked={removeCorrelatedFeatures}
                      onChange={() =>
                        setRemoveCorrelatedFeatures(
                          !removeCorrelatedFeatures
                        )
                      }
                    />

                    <div>
                      <strong>
                        Remove highly correlated features
                      </strong>

                      <span>
                        Discard redundant numeric columns above
                        threshold
                      </span>
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
                          setCorrelationThreshold(
                            Number(event.target.value)
                          )
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
                      onChange={() =>
                        setScalingMethod("none")
                      }
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
                      onChange={() =>
                        setScalingMethod("standard")
                      }
                    />

                    <div>
                      <strong>Standard scaling</strong>
                      <span>
                        Zero mean and unit variance
                      </span>
                    </div>
                  </label>

                  <label className="feature-source-option">
                    <input
                      type="radio"
                      name="scaling-method"
                      value="minmax"
                      checked={scalingMethod === "minmax"}
                      onChange={() =>
                        setScalingMethod("minmax")
                      }
                    />

                    <div>
                      <strong>Min-Max scaling</strong>
                      <span>
                        Scale numeric features to the 0–1 range
                      </span>
                    </div>
                  </label>

                  <label className="feature-source-option">
                    <input
                      type="radio"
                      name="scaling-method"
                      value="robust"
                      checked={scalingMethod === "robust"}
                      onChange={() =>
                        setScalingMethod("robust")
                      }
                    />

                    <div>
                      <strong>Robust scaling</strong>
                      <span>
                        Use median and interquartile range
                      </span>
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
                      checked={
                        pcaComponents === 0 &&
                        umapComponents === 0
                      }
                      onChange={() => {
                        setPcaComponents(0);
                        setUmapComponents(0);
                      }}
                    />

                    <div>
                      <strong>None</strong>
                      <span>
                        Do not compute dimensionality reduction
                      </span>
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
                      <span>
                        Compute pca_1 and pca_2
                      </span>
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
                          onChange={() =>
                            setPcaMode("add")
                          }
                        />

                        <div>
                          <strong>
                            Add PCA columns
                          </strong>

                          <span>
                            Keep original features and append
                            PCA columns
                          </span>
                        </div>
                      </label>

                      <label className="feature-source-option">
                        <input
                          type="radio"
                          name="pca-mode"
                          value="replace"
                          checked={pcaMode === "replace"}
                          onChange={() =>
                            setPcaMode("replace")
                          }
                        />

                        <div>
                          <strong>
                            Replace features with PCA
                          </strong>

                          <span>
                            Use only PCA columns as reduced
                            features
                          </span>
                        </div>
                      </label>

                      {scalingMethod === "none" && (
                        <p className="feature-warning">
                          PCA is usually recommended after
                          Standard scaling.
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
                      <span>
                        Compute umap_1 and umap_2
                      </span>
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
                          onChange={() =>
                            setUmapMode("add")
                          }
                        />

                        <div>
                          <strong>
                            Add UMAP columns
                          </strong>

                          <span>
                            Keep original features and append
                            UMAP columns
                          </span>
                        </div>
                      </label>

                      <label className="feature-source-option">
                        <input
                          type="radio"
                          name="umap-mode"
                          value="replace"
                          checked={umapMode === "replace"}
                          onChange={() =>
                            setUmapMode("replace")
                          }
                        />

                        <div>
                          <strong>
                            Replace features with UMAP
                          </strong>

                          <span>
                            Use only UMAP columns as reduced
                            features
                          </span>
                        </div>
                      </label>

                      {scalingMethod === "none" && (
                        <p className="feature-warning">
                          UMAP usually works better after
                          feature scaling.
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

              {buildError && (
                <p className="error-text">
                  {buildError}
                </p>
              )}
            </section>
          </>
        )}

     {isAntibodyDataset && (
      <section className="feature-builder-panel feature-panel-handcrafted">
        <div className="section-label">
          Antibody Sequence Features
        </div>

        <label className="feature-builder-field">
          Feature set name

          <input
            value={antibodyFeatureSetName}
            onChange={(event) =>
              setAntibodyFeatureSetName(event.target.value)
            }
            disabled={isGeneratingAntibodyFeatures}
          />
        </label>

        <p className="foundation-feature-description">
          Generates interpretable VH and VL sequence features:
          amino-acid frequencies, sequence length, hydrophobicity
          and charge fractions.
        </p>

        <Button
          onClick={handleGenerateAntibodyFeatureSet}
          disabled={
            isGeneratingAntibodyFeatures ||
            !antibodyFeatureSetName.trim()
          }
        >
          {isGeneratingAntibodyFeatures
            ? "Generating Features..."
            : "Generate Sequence Feature Set"}
        </Button>

        {antibodyFeaturesError && (
          <p className="error-text">
            {antibodyFeaturesError}
          </p>
        )}

        {antibodyFeaturesResult && (
          <div className="foundation-feature-result">
            <strong>
              {antibodyFeaturesResult.name}
            </strong>

            <span>
              {antibodyFeaturesResult.num_rows} antibodies ·{" "}
              {antibodyFeaturesResult.num_features} features
            </span>
          </div>
        )}
      </section>
    )}

      {isAntibodyDataset && (
        <section className="feature-builder-panel feature-panel-foundation">
          <div className="section-label">
            Foundation Model Features
          </div>

          <label className="feature-builder-field">
            Model

            <input
              value="ESM-2 650M"
              disabled
            />
          </label>

          <label className="feature-builder-field">
            Feature set name

            <input
              value={esmFeatureSetName}
              onChange={(event) =>
                setEsmFeatureSetName(event.target.value)
              }
              disabled={isGeneratingEsmFeatures}
            />
          </label>

          <p className="foundation-feature-description">
            Generates mean-pooled ESM-2 embeddings from the VH and VL
            sequences and concatenates them into 2560 features per antibody.
          </p>

          <Button
            onClick={handleGenerateEsmFeatureSet}
            disabled={
              isGeneratingEsmFeatures ||
              !esmFeatureSetName.trim()
            }
          >
            {isGeneratingEsmFeatures
              ? "Generating Embeddings..."
              : "Generate ESM Feature Set"}
          </Button>

          {esmFeaturesError && (
            <p className="error-text">
              {esmFeaturesError}
            </p>
          )}

          {esmFeaturesResult && (
            <div className="foundation-feature-result">
              <strong>
                {esmFeaturesResult.name}
              </strong>

              <span>
                {esmFeaturesResult.num_rows} antibodies ·{" "}
                {esmFeaturesResult.num_features} features
              </span>
            </div>
          )}
        </section>
      )}

        {!isAntibodyDataset && (
          <section className="feature-builder-panel feature-panel-foundation">
            <div className="section-label">
              Foundation Model Features
            </div>

            <label className="feature-builder-field">
              Model
              <input
                value="DINOv2 ViT-B/14"
                disabled
              />
            </label>

            <label className="feature-builder-field">
              Feature set name
              <input
                value={foundationFeatureSetName}
                onChange={(event) =>
                  setFoundationFeatureSetName(event.target.value)
                }
                disabled={isGeneratingFoundationFeatures}
                placeholder="DINOv2 Embeddings v1"
              />
            </label>

            <label className="feature-builder-field">
              Image channel
              <select
                value={foundationChannel}
                onChange={(event) =>
                  setFoundationChannel(event.target.value)
                }
                disabled={
                  isGeneratingFoundationFeatures ||
                  availableChannels.length === 0
                }
              >
                {availableChannels.length === 0 ? (
                  <option value="">
                    No channels available
                  </option>
                ) : (
                  availableChannels.map((channelName) => (
                    <option
                      key={channelName}
                      value={channelName}
                    >
                      {channelName}
                    </option>
                  ))
                )}
              </select>
            </label>

            <p className="foundation-feature-description">
              Generates one 768-dimensional DINOv2 embedding
              for each image using the selected channel.
            </p>

            <Button
              onClick={handleGenerateDINOv2FeatureSet}
              disabled={
                isGeneratingFoundationFeatures ||
                !foundationFeatureSetName.trim()
              }
            >
              {isGeneratingFoundationFeatures
                ? "Generating Embeddings..."
                : "Generate DINOv2 Feature Set"}
            </Button>

            {foundationFeaturesError && (
              <p className="error-text">
                {foundationFeaturesError}
              </p>
            )}

            {foundationFeaturesResult && (
              <div className="foundation-feature-result">
                <strong>
                  {foundationFeaturesResult.name}
                </strong>

                <span>
                  {foundationFeaturesResult.num_rows} images ·{" "}
                  {foundationFeaturesResult.num_features} embedding features
                </span>
              </div>
            )}
          </section>
        )}

          <section className="feature-builder-panel feature-panel-combine">
            <div className="section-label">
              Combine Feature Sets
            </div>

            <div className="feature-combine-selection">
              <span className="feature-combine-title">
                Select Feature Sets
              </span>

              {savedFeatureSets.length === 0 ? (
                <p>No saved Feature Sets available.</p>
              ) : (
                <div className="feature-source-list">
                  {savedFeatureSets.map((featureSet) => (
                    <label
                      key={featureSet.id}
                      className="feature-source-option"
                    >
                      <input
                        type="checkbox"
                        checked={selectedFeatureSetIds.includes(
                          featureSet.id
                        )}
                        onChange={() =>
                          handleToggleFeatureSet(featureSet.id)
                        }
                        disabled={isCombiningFeatureSets}
                      />

                      <div>
                        <strong>
                          {featureSet.name}
                        </strong>

                        <span>
                          {featureSet.num_features} features ·{" "}
                          {featureSet.num_rows} rows
                        </span>
                      </div>
                    </label>
                  ))}
                </div>
              )}

              <div className="feature-combine-summary">
                {selectedFeatureSetIds.length} Feature Sets selected
                {" · "}
                {selectedFeatureCount} input features
              </div>
            </div>

            <label className="feature-builder-field feature-combine-name">
              Combined Feature Set name

              <input
                value={combinedFeatureSetName}
                onChange={(event) =>
                  setCombinedFeatureSetName(event.target.value)
                }
                disabled={isCombiningFeatureSets}
              />
            </label>

            <Button
              onClick={handleCombineFeatureSets}
              disabled={
                isCombiningFeatureSets ||
                selectedFeatureSetIds.length < 2 ||
                !combinedFeatureSetName.trim()
              }
            >
              {isCombiningFeatureSets
                ? "Combining..."
                : `Combine ${selectedFeatureSetIds.length} Feature Sets`}
            </Button>

            {combineFeatureSetsError && (
              <p className="error-text">
                {combineFeatureSetsError}
              </p>
            )}

            {combineFeatureSetsResult && (
              <div className="foundation-feature-result">
                <strong>
                  {combineFeatureSetsResult.name}
                </strong>

                <span>
                  {combineFeatureSetsResult.num_rows} images ·{" "}
                  {combineFeatureSetsResult.num_features} features
                </span>
              </div>
            )}
          </section>

        <section className="feature-builder-panel feature-panel-saved">
          <div className="section-label">Saved Feature Sets</div>

          {savedFeatureSetsError && (
            <p className="error-text">{savedFeatureSetsError}</p>
          )}

          {savedFeatureSets.length === 0 ? (
            <p>No saved Feature Sets yet.</p>
          ) : (
            <div className="saved-feature-set-list">
              {savedFeatureSets.map((savedFeatureSet) => (
                <div
                  key={savedFeatureSet.id}
                  className="saved-feature-set-item"
                >
                  <div>
                    <strong>{savedFeatureSet.name}</strong>

                    <span>
                      {savedFeatureSet.num_rows} rows ·{" "}
                      {savedFeatureSet.num_features} features
                    </span>
                  </div>

                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    disabled={isDeletingFeatureSet}
                    onClick={() =>
                      handleDeleteFeatureSet(savedFeatureSet)
                    }
                  >
                    Delete
                  </Button>
                </div>
              ))}
            </div>
          )}
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