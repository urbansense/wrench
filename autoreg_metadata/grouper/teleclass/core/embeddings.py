from typing import Union

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Centralized service for generating embeddings."""

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        self.model_name = model_name
        self.encoder = SentenceTransformer(model_name)

    def get_embeddings(self, texts: Union[str, list[str]]) -> np.ndarray:
        return self.encoder.encode(texts)
