import { useEffect, useState } from "react";

function ImageViewer({
  activeDataset,
  selectedImage,
  overlayMode,
  foreground,
  selectedObjectLabel,
  analysisType,
}) {
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState("");

  useEffect(() => {
    setChannels([]);
    setSelectedChannel("");

    if (!selectedImage) {
      return;
    }

    fetch(`http://127.0.0.1:8002/images/${selectedImage.id}/channels`)
      .then((response) => response.json())
      .then((data) => {
        setChannels(data);

        if (data.length > 0) {
          setSelectedChannel(data[0].channel_name);
        }
      })
      .catch(() => {
        setChannels([]);
        setSelectedChannel("");
      });
  }, [selectedImage]);

  function buildChannelParams(extraParams = {}) {
    const params = new URLSearchParams(extraParams);

    if (selectedChannel) {
      params.set("channel", selectedChannel);
    }

    return params.toString();
  }

  function getPreviewImageUrl() {
    if (!activeDataset || !selectedImage) {
      return "";
    }

    if (overlayMode === "original") {
      const query = buildChannelParams();

      return `http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${selectedImage.id}/preview${
        query ? `?${query}` : ""
      }`;
    }

    const supportsObjectSelection =
      analysisType === "segmentation" ||
      analysisType === "morphology" ||
      analysisType === "intensity" ||
      analysisType === "texture";

    if (supportsObjectSelection && selectedObjectLabel !== null) {
      const query = buildChannelParams({
        foreground,
        t: String(Date.now()),
      });

      return `http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${selectedImage.id}/objects/${selectedObjectLabel}/overlay?${query}`;
    }

    if (overlayMode === "groundTruth") {
      return `http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${selectedImage.id}/ground-truth-overlay`;
    }

    const query = buildChannelParams({ foreground });

    return `http://127.0.0.1:8002/datasets/${activeDataset.id}/images/${selectedImage.id}/overlay?${query}`;
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

      {channels.length > 0 && (
        <div className="image-channel-selector">
          {channels.map((channel) => (
            <button
              key={channel.id}
              type="button"
              className={
                selectedChannel === channel.channel_name
                  ? "channel-button active"
                  : "channel-button"
              }
              onClick={() => setSelectedChannel(channel.channel_name)}
            >
              {channel.channel_name}
            </button>
          ))}
        </div>
      )}

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