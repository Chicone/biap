import { useEffect, useState } from "react";
import { ImageIcon } from "lucide-react";
import { getImages, uploadImage } from "@/services/imageService";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function ImagesTab({ activeDataset }) {
  const [images, setImages] = useState([]);

  useEffect(() => {
  async function loadImages() {
    if (!activeDataset) {
      setImages([]);
      return;
    }

    const data = await getImages(activeDataset.id);
    setImages(data);
  }

    loadImages();
  }, [activeDataset]);

  async function handleUploadImage(event) {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

  if (!activeDataset) return;

  const uploadedImage = await uploadImage(activeDataset.id, file);
    setImages((currentImages) => [
      ...currentImages,
      uploadedImage,
    ]);
  }

  return (
    <div className="workspace-content">
      <div className="dataset-header">
        <div>
          <h3>Images</h3>
          <p>Images associated with the selected dataset.</p>
        </div>

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

      {!activeDataset ? (
        <p>Select a dataset first from the Datasets tab.</p>
      ) : (
        <div className="image-grid">
          {images.map((image) => (
            <div className="image-card" key={image.id}>
              <img
                src={`http://127.0.0.1:8000${image.url}`}
                alt={image.filename}
                className="image-thumbnail"
              />

              <div>
                <strong>{image.filename}</strong>
                <p>{image.width} × {image.height}</p>
                <Badge>{image.modality || "Unknown"}</Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ImagesTab;