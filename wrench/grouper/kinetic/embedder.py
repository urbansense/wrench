from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity matrix between rows of a and rows of b."""
    a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-10)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return a @ b.T


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
            self.embedding_model = SentenceTransformer(embedder)

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


class OpenAIEmbedder(BaseEmbedder):
    """Embedder backed by any OpenAI-compatible embeddings endpoint.

    Works with OpenAI, Ollama (nomic-embed-text, mxbai-embed-large, …),
    and any other provider that exposes POST /v1/embeddings.
    """

    def __init__(
        self, model: str, base_url: str | None = None, api_key: str = "ollama"
    ):
        import openai

        self.embedding_model = model
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)

    def embed(
        self,
        documents: list[str],
        prompt: str | None = None,
        *args,
        **kwargs,
    ) -> np.ndarray:
        # OpenAI embeddings don't support instruction prompts — ignore prompt.
        # Batch in chunks of 2048 to stay within API limits.
        batch_size = 2048
        all_embeddings: list[np.ndarray] = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            response = self._client.embeddings.create(
                model=self.embedding_model, input=batch
            )
            vecs = np.array(
                [item.embedding for item in response.data], dtype=np.float32
            )
            all_embeddings.append(vecs)
        return np.vstack(all_embeddings)

    def similarity(
        self, embeddings: np.ndarray, other_embeddings: np.ndarray
    ) -> np.ndarray:
        return cosine_similarity(embeddings, other_embeddings)
