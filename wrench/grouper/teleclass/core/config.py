from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for the LLM service."""

    host: str = Field(description="LLM service host URL")
    model: str = Field(description="Model to use for LLM enrichment")
    prompt: str | None = Field(
        default=None, description="Prompt to generate key terms for enrichment"
    )
    temperature: float = Field(
        default=0.0, description="Temperature for LLM generation"
    )


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

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TELEClassConfig":
        """Load config from YAML file."""
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls.model_validate(config_dict)
