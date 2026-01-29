from typing import Any

from pydantic import BaseModel, Field

from wrench.utils.config import LLMConfig


class EmbeddingConfig(BaseModel):
    """Configuration for the embedding service."""

    model_name: str = Field(
        default="all-mpnet-base-v2",
        description="Name of the sentence transformer model",
    )


class CorpusConfig(BaseModel):
    """Configuration for corpus enrichment."""

    top_n: int = Field(default=5, description="Number of top phrases to extract")


class CacheConfig(BaseModel):
    """Configuration for caching."""

    enabled: bool = Field(
        default=True, description="Whether to enable caching, set to False by default"
    )
    directory: str = Field(
        default=".teleclass_cache", description="Directory for cache files"
    )


class TaxonomyMetadata(BaseModel):
    """Metadata about the taxonomy."""

    name: str = Field(default="", description="Name of the taxonomy")
    description: str = Field(
        default="", description="Description of the taxonomy's purpose"
    )


class TELEClassConfig(BaseModel):
    """Main configuration for TELEClass."""

    llm: LLMConfig
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    corpus: CorpusConfig = Field(default_factory=CorpusConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    taxonomy_metadata: TaxonomyMetadata = Field(
        description="Metadata about the taxonomy"
    )
    taxonomy: list[dict[str, Any]] = Field(
        description="Taxonomy structure in hierarchical format"
    )
