import numpy as np
import torch
import timm

from PIL import Image
from torchvision import transforms

from .base import VisionFoundationModel


class DinoV2(VisionFoundationModel):

    def __init__(self, model_name="vit_base_patch14_dinov2"):
        self.model_name = model_name
        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        self.model = None

        self.transform = transforms.Compose([
            transforms.Resize((518, 518)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        ])

    def load(self):

        if self.model is not None:
            return

        self.model = timm.create_model(
            self.model_name,
            pretrained=True,
            num_classes=0,
        )

        self.model.eval()
        self.model.to(self.device)

    def embed(self, image):
      self.load()

      if isinstance(image, np.ndarray):
        image = Image.fromarray(image)

      # DINOv2 expects a standard 3-channel image.
      # BBBC021 TIFFs can be 16-bit grayscale, so convert them explicitly.
      if image.mode not in ("RGB", "RGBA"):
        image = image.convert("I")

        image_array = np.asarray(image, dtype=np.float32)

        min_value = float(image_array.min())
        max_value = float(image_array.max())

        if max_value > min_value:
          image_array = (
            (image_array - min_value)
            / (max_value - min_value)
            * 255.0
          )
        else:
          image_array = np.zeros_like(
            image_array,
            dtype=np.float32,
          )

        image = Image.fromarray(
          image_array.astype(np.uint8),
          mode="L",
        ).convert("RGB")
      else:
        image = image.convert("RGB")

      tensor = self.transform(image)
      tensor = tensor.unsqueeze(0).to(self.device)

      with torch.no_grad():
        embedding = self.model(tensor)

      return embedding.squeeze(0).cpu().numpy()

_dinov2_instance = None

def get_dinov2_model():
  global _dinov2_instance

  if _dinov2_instance is None:
    _dinov2_instance = DinoV2()

  return _dinov2_instance