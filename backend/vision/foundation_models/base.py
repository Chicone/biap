from abc import ABC, abstractmethod


class VisionFoundationModel(ABC):
    """Base class for all vision foundation models."""

    @abstractmethod
    def load(self):
        """Load model weights."""
        pass

    @abstractmethod
    def embed(self, image):
        """Return a feature vector for one image."""
        pass