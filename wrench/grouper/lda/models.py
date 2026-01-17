from typing import Any

from pydantic import BaseModel, Field

from wrench.models import Device


class LDATopic(BaseModel):
    """Represents a topic discovered by LDA with associated metadata."""

    id: int = Field(description="Topic ID")
    name: str = Field(description="Human-readable topic name")
    description: str = Field(default="", description="Topic description")
    keywords: list[str] = Field(
        default_factory=list, description="Top keywords for the topic"
    )
    word_distribution: dict[str, float] = Field(
        default_factory=dict, description="Word-probability distribution"
    )
    devices: list[Device] = Field(
        default_factory=list, description="Devices assigned to this topic"
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict, description="Device ID to confidence score mapping"
    )
    original_topic_ids: list[int] = Field(
        default_factory=list,
        description="Original LDA topic IDs that were merged into this topic",
    )

    model_config = {"arbitrary_types_allowed": True}

    def add_device(self, device: Device, confidence: float) -> None:
        """Add a device to this topic with its confidence score."""
        self.devices.append(device)
        self.confidence_scores[device.id] = confidence


class LDAResult(BaseModel):
    """Container for LDA modeling results."""

    topics: list[LDATopic] = Field(description="Discovered topics")
    document_topic_matrix: Any = Field(description="Document-topic probability matrix")
    feature_names: list[str] = Field(description="Vocabulary features")
    perplexity: float = Field(default=0.0, description="Model perplexity score")

    model_config = {"arbitrary_types_allowed": True}


class LDAConfig(BaseModel):
    """Configuration for LDA grouper."""

    n_topics: int = Field(default=10, description="Number of topics to discover")
    max_iter: int = Field(default=100, description="Maximum iterations for LDA")
    alpha: float = Field(default=0.1, description="Document-topic concentration")
    beta: float = Field(default=0.01, description="Topic-word concentration")
    min_df: int = Field(default=2, description="Minimum document frequency for words")
    max_df: float = Field(
        default=0.8, description="Maximum document frequency for words"
    )
    max_features: int = Field(default=1000, description="Maximum number of features")
    similarity_threshold: float = Field(
        default=0.1, description="Minimum similarity threshold for topic assignment"
    )
    random_state: int = Field(
        default=42, description="Random state for reproducibility"
    )
    top_words: int = Field(
        default=10, description="Number of top words to extract per topic"
    )

    # Topic naming configuration
    use_llm_naming: bool = Field(default=True, description="Use LLM for topic naming")

    # Output configuration
    save_analysis: bool = Field(
        default=False, description="Save topic analysis to files"
    )
    analysis_output_dir: str = Field(
        default="lda_analysis", description="Directory to save analysis files"
    )


class OptimizationConfig(BaseModel):
    """Configuration for hyperparameter optimization."""

    param_grid: dict[str, list] = Field(
        default_factory=dict, description="Parameter ranges to search"
    )
    metric_weights: dict[str, float] = Field(
        default_factory=dict, description="Weights for evaluation metrics"
    )
    enabled: bool = Field(default=False, description="Enable optimization")
