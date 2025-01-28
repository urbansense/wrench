import numpy as np
from pydantic import BaseModel, ConfigDict, computed_field

from .models import DocumentMeta


class TermScore(BaseModel):
    """Store terms and scores for a candidate term, used in enrichment process"""

    term: str
    popularity: float | None = None
    distinctiveness: float | None = None
    semantic_similarity: float | None = None

    @property
    def affinity_score(self) -> float:
        """Calculate geometric mean of scores"""

        if (
            self.popularity is None
            or self.distinctiveness is None
            or self.semantic_similarity is None
        ):
            raise ValueError("Values are not available before corpus enrichment")

        return np.cbrt(
            self.popularity * self.distinctiveness * self.semantic_similarity
        )

    def __hash__(self) -> int:
        """Make hashable based on term"""
        return hash(self.term)

    def __eq__(self, other: object) -> bool:
        """Check equality based on term"""
        if not isinstance(other, TermScore):
            return NotImplemented
        return self.term == other.term


class EnrichedClass(BaseModel):
    """Represents an enriched class with metadata and assigned terms"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class_name: str
    class_description: str = ""
    terms: set[TermScore]
    embeddings: np.ndarray | None = None


class EnrichmentResult(BaseModel):
    """Container for enrichment results"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ClassEnrichment: dict[str, EnrichedClass]


class LLMEnrichmentResult(EnrichmentResult):
    # Stores LLM enrichment results, such as classes with its relevant terms, and each document's core classes
    DocumentCoreClasses: list[DocumentMeta]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def result(self) -> tuple[dict[str, EnrichedClass], list[DocumentMeta]]:
        return self.ClassEnrichment, self.DocumentCoreClasses


class CorpusEnrichmentResult(EnrichmentResult):
    # Stores Corpus enrichment results, such as enriched classes with relevant terms
    @computed_field  # type: ignore[prop-decorator]
    @property
    def result(self) -> dict[str, EnrichedClass]:
        return self.ClassEnrichment
