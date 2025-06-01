from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


class BaseEmbedder(ABC):
    embedding_model: Any

    @abstractmethod
    def embed(
        self,
        documents: list[str],
        prompt: str | None = None,
        *args,
        **kwargs,
    ) -> np.ndarray:
        pass

    @abstractmethod
    def similarity(
        self, embeddings: np.ndarray, other_embeddings: np.ndarray
    ) -> np.ndarray:
        pass


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, embedder: str | SentenceTransformer):
        if isinstance(embedder, SentenceTransformer):
            self.embedding_model: SentenceTransformer = embedder
        elif isinstance(embedder, str):
            self.embedding_model: SentenceTransformer = SentenceTransformer(embedder)

    def embed(
        self,
        documents: list[str],
        prompt: str | None = None,
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        """Embed a list of documents into matrix embeddings.

        Args:
            documents: A list of documents or words to be embedded.
            prompt: Optional prompt to pass in to the model.
            normalize_embeddings: Normalize vectors to have length 1.

        Returns:
            Document/words embeddings with shape (n, m) with `n` documents/words
            that each have an embeddings size of `m`.
        """
        embeddings = self.embedding_model.encode(
            documents,
            prompt=prompt,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=True,
        )
        return embeddings

    def similarity(
        self, embeddings: np.ndarray, other_embeddings: np.ndarray
    ) -> np.ndarray:
        return self.embedding_model.similarity(embeddings, other_embeddings).numpy()
