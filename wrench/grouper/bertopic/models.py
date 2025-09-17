"""Data models for BERTopic grouper."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from wrench.models import Device


class BERTopicTopic(BaseModel):
    """Represents a topic discovered by BERTopic with associated metadata."""

    id: int = Field(description="Topic ID")
    name: str = Field(description="Human-readable topic name")
    description: str = Field(default="", description="Topic description")
    keywords: list[str] = Field(
        default_factory=list, description="Top keywords for the topic"
    )
    word_scores: dict[str, float] = Field(
        default_factory=dict, description="Word-score distribution"
    )
    devices: list[Device] = Field(
        default_factory=list, description="Devices assigned to this topic"
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict, description="Device ID to confidence score mapping"
    )
    representative_docs: list[str] = Field(
        default_factory=list, description="Representative documents for this topic"
    )

    model_config = {"arbitrary_types_allowed": True}

    def add_device(self, device: Device, confidence: float) -> None:
        """Add a device to this topic with its confidence score."""
        self.devices.append(device)
        self.confidence_scores[device.id] = confidence


class BERTopicResult(BaseModel):
    """Container for BERTopic modeling results."""

    topics: list[BERTopicTopic] = Field(description="Discovered topics")
    topic_model: Any = Field(description="Trained BERTopic model")
    embeddings: Any = Field(description="Document embeddings")
    topic_assignments: list[int] = Field(
        description="Topic assignments for each document"
    )
    probabilities: Optional[Any] = Field(
        default=None, description="Topic probabilities for each document"
    )

    model_config = {"arbitrary_types_allowed": True}


class BERTopicConfig(BaseModel):
    """Configuration for BERTopic grouper."""

    # Core BERTopic parameters
    nr_topics: Optional[int] = Field(
        default=None, description="Number of topics to discover (auto if None)"
    )
    min_topic_size: int = Field(
        default=10, description="Minimum number of documents per topic"
    )

    # Embedding model configuration
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence transformer model name"
    )

    # UMAP parameters
    umap_n_neighbors: int = Field(
        default=15, description="Number of neighbors for UMAP"
    )
    umap_n_components: int = Field(
        default=5, description="Number of components for UMAP"
    )
    umap_min_dist: float = Field(default=0.0, description="Minimum distance for UMAP")
    umap_metric: str = Field(default="cosine", description="Distance metric for UMAP")

    # HDBSCAN parameters
    hdbscan_min_cluster_size: int = Field(
        default=10, description="Minimum cluster size for HDBSCAN"
    )
    hdbscan_metric: str = Field(
        default="euclidean", description="Distance metric for HDBSCAN"
    )
    hdbscan_cluster_selection_method: str = Field(
        default="eom", description="Cluster selection method for HDBSCAN"
    )

    # Topic representation
    top_n_words: int = Field(default=10, description="Number of top words per topic")

    # Filtering
    similarity_threshold: float = Field(
        default=0.1, description="Minimum similarity threshold for topic assignment"
    )

    # Reproducibility
    random_state: int = Field(
        default=42, description="Random state for reproducibility"
    )

    # Topic naming configuration
    use_llm_naming: bool = Field(default=True, description="Use LLM for topic naming")

    # Output configuration
    save_analysis: bool = Field(
        default=False, description="Save topic analysis to files"
    )
    analysis_output_dir: str = Field(
        default="bertopic_analysis", description="Directory to save analysis files"
    )

    # Performance
    calculate_probabilities: bool = Field(
        default=False,
        description="Calculate topic probabilities (slower but more accurate)",
    )
