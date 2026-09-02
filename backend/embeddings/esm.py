import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


MODEL_NAME = "facebook/esm2_t33_650M_UR50D"


class ESMEmbedder:
  def __init__(self):
    self.device = torch.device(
      "mps"
      if torch.backends.mps.is_available()
      else "cuda"
      if torch.cuda.is_available()
      else "cpu"
    )

    self.tokenizer = AutoTokenizer.from_pretrained(
      MODEL_NAME
    )

    self.model = AutoModel.from_pretrained(
      MODEL_NAME
    )

    self.model.to(self.device)
    self.model.eval()

  @torch.inference_mode()
  def embed_sequence(
    self,
    sequence: str,
  ) -> np.ndarray:
    sequence = sequence.strip().upper()

    inputs = self.tokenizer(
      sequence,
      return_tensors="pt",
      add_special_tokens=True,
    )

    inputs = {
      key: value.to(self.device)
      for key, value in inputs.items()
    }

    outputs = self.model(**inputs)

    hidden = outputs.last_hidden_state[0]

    # Exclude BOS and EOS tokens.
    residue_embeddings = hidden[1:-1]

    embedding = residue_embeddings.mean(dim=0)

    return (
      embedding
      .detach()
      .cpu()
      .numpy()
      .astype(np.float32)
    )

  def embed_antibody(
    self,
    heavy_sequence: str,
    light_sequence: str,
  ) -> np.ndarray:
    heavy_embedding = self.embed_sequence(
      heavy_sequence
    )

    light_embedding = self.embed_sequence(
      light_sequence
    )

    return np.concatenate(
      [
        heavy_embedding,
        light_embedding,
      ]
    )