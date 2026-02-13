from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import openai
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


class OllamaEmbedder(BaseEmbedder):
    """Embedder that uses a remote Ollama-compatible embeddings API."""

    def __init__(self, base_url: str, model: str, api_key: str = "ollama"):
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        # Set embedding_model to self so KeyBERT can use encode() directly.
        self.embedding_model = self

    def embed(
        self,
        documents: list[str],
        prompt: str | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Embed documents using the remote Ollama API.

        Args:
            documents: A list of documents or words to be embedded.
            prompt: Optional prompt prepended to each document.
            **kwargs: Any non-used parameter

        Returns:
            Document embeddings with shape (n, m).
        """
        if prompt:
            documents = [f"{prompt}{doc}" for doc in documents]

        response = self._client.embeddings.create(model=self._model, input=documents)
        embeddings = np.array([item.embedding for item in response.data])

        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms

        return embeddings

    def encode(
        self,
        documents: list[str],
        prompt: str | None = None,
        show_progress_bar: bool = False,
        **kwargs,
    ) -> np.ndarray:
        """KeyBERT-compatible encode method. Delegates to embed()."""
        return self.embed(documents, prompt=prompt)

    def similarity(
        self, embeddings: np.ndarray, other_embeddings: np.ndarray
    ) -> np.ndarray:
        # Cosine similarity (embeddings are already normalized)
        return embeddings @ other_embeddings.T
