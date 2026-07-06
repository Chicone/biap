import { Badge } from "@/components/ui/badge";

function ImageBrowser({ images, selectedImage, onSelectImage }) {
  return (
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
            onClick={() => onSelectImage(image)}
          >
            <img
              src={`http://127.0.0.1:8000${image.url}`}
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
  );
}

export default ImageBrowser;