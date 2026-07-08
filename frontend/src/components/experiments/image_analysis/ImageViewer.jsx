function ImageViewer({
  activeDataset,
  selectedImage,
  overlayMode,
  foreground,
  selectedObjectLabel,
  analysisType,
}) {
  function getPreviewImageUrl() {
    if (!activeDataset || !selectedImage) {
      return "";
    }

    if (overlayMode === "original") {
      return `http://127.0.0.1:8000${selectedImage.url}`;
    }

    const supportsObjectSelection =
      analysisType === "segmentation" ||
      analysisType === "morphology" ||
      analysisType === "intensity" ||
      analysisType === "texture";

    if (supportsObjectSelection && selectedObjectLabel !== null) {
      return `http://127.0.0.1:8000/datasets/${activeDataset.id}/images/${selectedImage.id}/objects/${selectedObjectLabel}/overlay?foreground=${foreground}&t=${Date.now()}`;    }

    if (overlayMode === "groundTruth") {
      return `http://127.0.0.1:8000/datasets/${activeDataset.id}/images/${selectedImage.id}/ground-truth-overlay`;
    }

    return `http://127.0.0.1:8000/datasets/${activeDataset.id}/images/${selectedImage.id}/overlay?foreground=${foreground}`;
  }

  if (!selectedImage) {
    return (
      <div className="image-preview empty-inspector">
        <p>Select an image to preview and analyze.</p>
      </div>
    );
  }

  return (
    <section className="selected-image-section">
      <div className="section-label">Image Preview</div>

      <div className="image-preview-header">
        <div>
          <h3>{selectedImage.filename}</h3>
          <p>
            {selectedImage.width} × {selectedImage.height} ·{" "}
            {selectedImage.modality || "Unknown"}
          </p>
        </div>
      </div>

      <div className="image-preview-figure">
        <img
          src={getPreviewImageUrl()}
          alt={selectedImage.filename}
          className="image-preview-large"
        />
      </div>
    </section>
  );
}

export default ImageViewer;