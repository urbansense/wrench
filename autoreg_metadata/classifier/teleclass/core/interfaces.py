# core/interfaces.py
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import numpy as np


@runtime_checkable
class EmbeddingService(Protocol):
    def get_embeddings(self, texts: str | list[str]) -> np.ndarray: ...


@runtime_checkable
class Enricher(Protocol):
    def enrich(self, context: dict) -> dict: ...


@runtime_checkable
class CacheProvider(Protocol):
    def save_class_terms(self, class_terms: dict): ...
    def load_class_terms(self) -> dict | None: ...
