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
import ImageViewer from "@/components/experiments/image_analysis/ImageViewer";
import ImageBrowser from "@/components/experiments/image_analysis/ImageBrowser";
import SegmentationPanel from "@/components/experiments/image_analysis/segmentation/SegmentationPanel";
import SegmentationResults from "@/components/experiments/image_analysis/segmentation/SegmentationResults";
import AnalysisSelector from "@/components/experiments/image_analysis/AnalysisSelector";

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

  const [analysisType, setAnalysisType] = useState("segmentation");

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
  <section className="image-inspector-top">
    <div className="image-preview">
      <ImageViewer
        activeDataset={activeDataset}
        selectedImage={selectedImage}
        overlayMode={overlayMode}
        foreground={foreground}
      />

     {selectedImage && (
      <>
        <AnalysisSelector
          analysisType={analysisType}
          setAnalysisType={setAnalysisType}
        />

        {analysisType === "segmentation" && (
          <>
            <SegmentationPanel
              foreground={foreground}
              setForeground={setForeground}
              overlayMode={overlayMode}
              setOverlayMode={setOverlayMode}
              setAnalysis={setAnalysis}
              setEvaluation={setEvaluation}
              isAnalyzing={isAnalyzing}
              onRunSegmentation={handleAnalyzeImage}
            />

            <SegmentationResults
              analysis={analysis}
              analysisError={analysisError}
              evaluation={evaluation}
              evaluationError={evaluationError}
            />
          </>
        )}
      </>
    )}
    </div>
  </section>

  <ImageBrowser
    images={images}
    selectedImage={selectedImage}
    onSelectImage={handleSelectImage}
  />
</div>
      )}
    </div>
  );
}

export default ImagesTab;
