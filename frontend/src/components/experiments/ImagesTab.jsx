import { useEffect, useState } from "react";
import {
  analyzeImage,
  evaluateImage,
  getImages,
  importFolder,
  uploadImage,
} from "@/services/imageService";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const API_URL = "http://127.0.0.1:8000";

function ImagesTab({ activeDataset }) {
  const [images, setImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [folderPath, setFolderPath] = useState("");

  const [overlayMode, setOverlayMode] = useState("original");
  const [segmentationMethod, setSegmentationMethod] = useState("otsu");
  const [foreground, setForeground] = useState("bright");

  const [analysis, setAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  const [evaluation, setEvaluation] = useState(null);
  const [evaluationError, setEvaluationError] = useState(null);

  useEffect(() => {
    async function loadImages() {
      if (!activeDataset) {
        setImages([]);
        setSelectedImage(null);
        return;
      }

      const data = await getImages(activeDataset.id);
      setImages(data);
    }

    loadImages();
  }, [activeDataset]);

  async function handleUploadImage(event) {
    const file = event.target.files[0];

    if (!file || !activeDataset) {
      return;
    }

    const uploadedImage = await uploadImage(activeDataset.id, file);
    setImages((currentImages) => [...currentImages, uploadedImage]);
  }

  async function handleImportFolder() {
    if (!activeDataset || !folderPath) {
      return;
    }

    await importFolder(activeDataset.id, folderPath);

    const updatedImages = await getImages(activeDataset.id);
    setImages(updatedImages);
  }

  function clearResults() {
    setAnalysis(null);
    setAnalysisError(null);
    setEvaluation(null);
    setEvaluationError(null);
  }

  function handleSelectImage(image) {
    setSelectedImage(image);
    setOverlayMode("original");
    clearResults();
  }

  async function handleAnalyzeImage() {
    if (!activeDataset || !selectedImage) {
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);
    setEvaluationError(null);
    setEvaluation(null);

    try {
      const result = await analyzeImage(
        activeDataset.id,
        selectedImage.id,
        foreground
      );

      setAnalysis(result);

      const evaluationResult = await evaluateImage(
        activeDataset.id,
        selectedImage.id,
        foreground
      );

      setEvaluation(evaluationResult);
      setOverlayMode("prediction");
    } catch (error) {
      setAnalysisError("Segmentation analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  }

  function getPreviewImageUrl() {
    if (!activeDataset || !selectedImage) {
      return "";
    }

    if (overlayMode === "original") {
      return `${API_URL}${selectedImage.url}`;
    }

    if (overlayMode === "groundTruth") {
      return `${API_URL}/datasets/${activeDataset.id}/images/${selectedImage.id}/ground-truth-overlay`;
    }

    return `${API_URL}/datasets/${activeDataset.id}/images/${selectedImage.id}/overlay?foreground=${foreground}`;
  }

  return (
    <div className="workspace-content">
      <div className="images-toolbar">
        <div>
          <h3>Images</h3>
          <p>Browse, inspect and analyze images for this dataset.</p>
        </div>

        <div className="image-actions">
          <label>
            <input
              type="file"
              accept="image/*"
              onChange={handleUploadImage}
              hidden
            />

            <Button asChild>
              <span>+ Import Image</span>
            </Button>
          </label>
        </div>
      </div>

      <div className="folder-import-panel">
        <input
          value={folderPath}
          onChange={(event) => setFolderPath(event.target.value)}
          placeholder="/Users/luiscamara/PyCharm/biap/data/external/BBBC038/stage1_train"
        />

        <Button onClick={handleImportFolder}>Import Folder</Button>
      </div>

      {!activeDataset ? (
        <p>Select a dataset first from the Datasets tab.</p>
      ) : (
        <div className="image-workbench">
          <section className="image-inspector">
            {selectedImage ? (
              <div className="image-preview">
                <div className="image-preview-header">
                  <div>
                    <span className="section-label">Selected image</span>
                    <h3>{selectedImage.filename}</h3>
                    <p>
                      {selectedImage.width} × {selectedImage.height} ·{" "}
                      {selectedImage.modality || "Unknown"}
                    </p>
                  </div>
                </div>

                <div className="selected-image-panel">
                  <img
                    src={getPreviewImageUrl()}
                    alt={selectedImage.filename}
                    className="image-preview-large"
                  />
                </div>

                <div className="analysis-module">
                  <div className="analysis-module-header">
                    <div>
                      <span className="section-label">Segmentation</span>
                      <h4>Configure and run segmentation</h4>
                    </div>

                    <Button
                      onClick={handleAnalyzeImage}
                      disabled={isAnalyzing}
                    >
                      {isAnalyzing ? "Running..." : "Run Segmentation"}
                    </Button>
                  </div>

                  <div className="segmentation-controls-grid">
                    <label>
                      Method
                      <select
                        value={segmentationMethod}
                        onChange={(event) =>
                          setSegmentationMethod(event.target.value)
                        }
                      >
                        <option value="otsu">Otsu thresholding</option>
                      </select>
                    </label>

                    <label>
                      Foreground
                      <select
                        value={foreground}
                        onChange={(event) => {
                          setForeground(event.target.value);
                          setOverlayMode("original");
                          clearResults();
                        }}
                      >
                        <option value="bright">Bright objects</option>
                        <option value="dark">Dark objects</option>
                      </select>
                    </label>

                    <div>
                      <span className="control-label">View</span>

                      <div className="image-preview-actions">
                        <Button
                          onClick={() => setOverlayMode("original")}
                          variant={
                            overlayMode === "original" ? "default" : "secondary"
                          }
                        >
                          Original
                        </Button>

                        <Button
                          onClick={() => setOverlayMode("prediction")}
                          variant={
                            overlayMode === "prediction"
                              ? "default"
                              : "secondary"
                          }
                        >
                          Prediction
                        </Button>

                        <Button
                          onClick={() => setOverlayMode("groundTruth")}
                          variant={
                            overlayMode === "groundTruth"
                              ? "default"
                              : "secondary"
                          }
                        >
                          Ground Truth
                        </Button>
                      </div>
                    </div>
                  </div>

                  {analysisError && (
                    <p className="error-text">{analysisError}</p>
                  )}
                </div>

                {(analysis || evaluation || evaluationError) && (
                  <div className="analysis-panels">
                    {analysis && (
                      <div className="analysis-panel">
                        <div className="analysis-header">
                          <h4>Segmentation Analysis</h4>
                          <Badge>{analysis.num_objects} objects</Badge>
                        </div>

                        <dl className="metric-list">
                          <div>
                            <dt>Method</dt>
                            <dd>Otsu</dd>
                          </div>

                          <div>
                            <dt>Threshold</dt>
                            <dd>{analysis.threshold}</dd>
                          </div>

                          <div>
                            <dt>Detected objects</dt>
                            <dd>{analysis.num_objects}</dd>
                          </div>
                        </dl>

                        <h5>First detected objects</h5>

                        <div className="analysis-table">
                          <div className="analysis-row analysis-row-header">
                            <span>Object</span>
                            <span>Area</span>
                            <span>Centroid</span>
                          </div>

                          {analysis.objects.slice(0, 5).map((object) => (
                            <div className="analysis-row" key={object.label}>
                              <span>{object.label}</span>
                              <span>{object.area}</span>
                              <span>
                                ({object.centroid[0].toFixed(1)},{" "}
                                {object.centroid[1].toFixed(1)})
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {evaluationError && (
                      <p className="error-text">{evaluationError}</p>
                    )}

                    {evaluation && (
                      <div className="analysis-panel">
                        <div className="analysis-header">
                          <h4>Ground-truth Evaluation</h4>
                          <Badge>{evaluation.foreground}</Badge>
                        </div>

                        <dl className="metric-list">
                          <div>
                            <dt>Method</dt>
                            <dd>Otsu</dd>
                          </div>

                          <div>
                            <dt>IoU</dt>
                            <dd>{evaluation.iou.toFixed(3)}</dd>
                          </div>

                          <div>
                            <dt>Dice</dt>
                            <dd>{evaluation.dice.toFixed(3)}</dd>
                          </div>

                          <div>
                            <dt>Precision</dt>
                            <dd>{evaluation.precision.toFixed(3)}</dd>
                          </div>

                          <div>
                            <dt>Recall</dt>
                            <dd>{evaluation.recall.toFixed(3)}</dd>
                          </div>
                        </dl>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="image-preview empty-inspector">
                <p>Select an image to preview and analyze.</p>
              </div>
            )}
          </section>

          <section className="image-browser">
            <div className="image-browser-header">
              <h4>Dataset images</h4>
              <span>{images.length} images</span>
            </div>

            <div className="image-grid">
              {images.map((image) => (
                <div
                  className={
                    selectedImage?.id === image.id
                      ? "image-card image-card-selected"
                      : "image-card"
                  }
                  key={image.id}
                  onClick={() => handleSelectImage(image)}
                >
                  <img
                    src={`${API_URL}${image.url}`}
                    alt={image.filename}
                    className="image-thumbnail"
                  />

                  <div>
                    <strong>{image.filename}</strong>
                    <p>
                      {image.width} × {image.height}
                    </p>
                    <Badge>{image.modality || "Unknown"}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default ImagesTab;
