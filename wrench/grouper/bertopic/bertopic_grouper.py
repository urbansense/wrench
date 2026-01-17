"""BERTopic-based grouper for clustering devices."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import validate_call

from wrench.grouper.base import BaseGrouper
from wrench.log import logger
from wrench.models import Device, Group
from wrench.utils.config import LLMConfig

from .models import BERTopicConfig, BERTopicResult, BERTopicTopic

try:
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sentence_transformers import SentenceTransformer
    from umap import UMAP
except ImportError as e:
    raise ImportError(
        "BERTopic dependencies not installed. \
            Install with: pip install auto-wrench[bertopic]"
    ) from e


class BERTopicGrouper(BaseGrouper):
    """BERTopic-based grouper for discovering topics and clustering devices.

    This grouper uses BERTopic to discover topics from device descriptions and metadata,
    then assigns devices to topics based on similarity calculations. It uses modern
    transformer-based embeddings with UMAP dimensionality reduction and HDBSCAN
    clustering.
    """

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        config: BERTopicConfig,
        llm_config: Optional[LLMConfig] = None,
    ):
        """Initialize BERTopic grouper.

        Args:
            config: BERTopic configuration
            llm_config: LLM configuration for topic naming (optional)
        """
        self.config = config
        self.llm_config = llm_config
        self.logger = logger.getChild(self.__class__.__name__)

        # Initialize components
        self.topic_model: Optional[BERTopic] = None
        self.bertopic_result: Optional[BERTopicResult] = None
        self.embedding_model: Optional[SentenceTransformer] = None

        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(config.embedding_model)
            self.logger.info(f"Loaded embedding model: {config.embedding_model}")
        except Exception as e:
            self.logger.warning(f"Failed to load embedding model: {e}")
            self.embedding_model = None

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for BERTopic modeling.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text
        """
        # Convert to lowercase
        text = text.lower()

        # Remove special characters but keep spaces
        text = re.sub(r"[^a-zA-Z\s]", " ", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        return text

    def _extract_device_text(self, device: Device) -> str:
        """Extract text content from device for topic modeling.

        Args:
            device: Device to extract text from

        Returns:
            Combined text content
        """
        text_parts = []

        # Add device name if available
        if device.name:
            text_parts.append(device.name)

        # Add description if available
        if device.description:
            text_parts.append(device.description)

        # Add datastream names
        if device.datastreams:
            text_parts.extend(device.datastreams)

        # Add sensor names
        if device.sensors:
            text_parts.extend(device.sensors)

        # Add observed properties
        if device.observed_properties:
            text_parts.extend(device.observed_properties)

        # Combine and preprocess
        combined_text = " ".join(text_parts)
        return self._preprocess_text(combined_text)

    def _create_bertopic_model(self) -> BERTopic:
        """Create and configure BERTopic model.

        Returns:
            Configured BERTopic model
        """
        # Initialize UMAP for dimensionality reduction
        umap_model = UMAP(
            n_neighbors=self.config.umap_n_neighbors,
            n_components=self.config.umap_n_components,
            min_dist=self.config.umap_min_dist,
            metric=self.config.umap_metric,
            random_state=self.config.random_state,
        )

        # Initialize HDBSCAN for clustering
        hdbscan_model = HDBSCAN(
            min_cluster_size=self.config.hdbscan_min_cluster_size,
            metric=self.config.hdbscan_metric,
            cluster_selection_method=self.config.hdbscan_cluster_selection_method,
            prediction_data=True,
        )

        # Create BERTopic model
        topic_model = BERTopic(
            embedding_model=self.embedding_model,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            nr_topics=self.config.nr_topics,
            min_topic_size=self.config.min_topic_size,
            top_n_words=self.config.top_n_words,
            calculate_probabilities=self.config.calculate_probabilities,
            verbose=True,
        )

        return topic_model

    def _fit_bertopic_model(self, documents: list[str]) -> BERTopicResult:
        """Fit BERTopic model on documents.

        Args:
            documents: List of document texts

        Returns:
            BERTopic modeling results
        """
        self.logger.info(f"Fitting BERTopic model on {len(documents)} documents")

        # Create BERTopic model
        self.topic_model = self._create_bertopic_model()

        # Fit model and transform documents
        topics, probabilities = self.topic_model.fit_transform(documents)

        # Get embeddings
        embeddings = self.topic_model._extract_embeddings(documents)

        self.logger.info(
            f"BERTopic model fitted. \
                Found {len(self.topic_model.get_topic_info())} topics"
        )

        return BERTopicResult(
            topics=[],  # Will be populated later
            topic_model=self.topic_model,
            embeddings=embeddings,
            topic_assignments=topics,
            probabilities=probabilities,
        )

    def _create_topics_from_bertopic(self) -> list[BERTopicTopic]:
        """Create BERTopicTopic objects from fitted BERTopic model.

        Returns:
            List of BERTopic topics with names and descriptions
        """
        if not self.topic_model:
            return []

        topics = []
        topic_info = self.topic_model.get_topic_info()

        for _, row in topic_info.iterrows():
            topic_id = row["Topic"]

            # Skip outlier topic (-1)
            if topic_id == -1:
                continue

            # Get topic words and scores
            topic_words = self.topic_model.get_topic(topic_id)
            keywords = [word for word, _ in topic_words]
            word_scores = {word: float(score) for word, score in topic_words}

            # Get representative documents
            representative_docs = []
            try:
                repr_docs = self.topic_model.get_representative_docs(topic_id)
                representative_docs = repr_docs[:3]  # Top 3 representative docs
            except Exception as e:
                self.logger.debug(
                    f"Could not get representative docs for topic {topic_id}: {e}"
                )

            # Create topic name (simple approach - use top keywords)
            topic_name = f"Topic_{topic_id}_{'-'.join(keywords[:3])}"

            # Create topic description
            topic_description = f"Topic characterized by: {', '.join(keywords[:5])}"

            topic = BERTopicTopic(
                id=topic_id,
                name=topic_name,
                description=topic_description,
                keywords=keywords,
                word_scores=word_scores,
                representative_docs=representative_docs,
            )

            topics.append(topic)
            self.logger.debug(f"Created topic {topic_id}: {topic_name}")

        return topics

    def _assign_devices_to_topics(
        self, devices: list[Device], topics: list[BERTopicTopic]
    ) -> list[BERTopicTopic]:
        """Assign devices to topics based on model predictions.

        Args:
            devices: List of devices to assign
            topics: List of topics to assign to

        Returns:
            Topics with assigned devices
        """
        topic_assignments = self.bertopic_result.topic_assignments
        probabilities = self.bertopic_result.probabilities

        # Create topic ID to topic object mapping
        topic_map = {topic.id: topic for topic in topics}

        for device_idx, device in enumerate(devices):
            assigned_topic_id = topic_assignments[device_idx]

            # Skip outlier assignments
            if assigned_topic_id == -1:
                self.logger.debug(
                    f"Device {device.id} assigned to outlier topic, skipping"
                )
                continue

            # Get confidence score
            confidence = 1.0  # Default confidence
            if probabilities is not None and len(probabilities) > device_idx:
                # probabilities[device_idx] is an array of probabilities for each topic
                # Get the probability for the assigned topic
                topic_probs = probabilities[device_idx]
                if (
                    hasattr(topic_probs, "__len__")
                    and len(topic_probs) > assigned_topic_id
                ):
                    confidence = float(topic_probs[assigned_topic_id])
                else:
                    # If it's a single value, use it directly
                    confidence = float(topic_probs)

            # Check if confidence meets threshold
            if confidence < self.config.similarity_threshold:
                self.logger.debug(
                    f"Device {device.id} confidence {confidence:.3f} below threshold, \
                        skipping"
                )
                continue

            # Assign device to topic
            if assigned_topic_id in topic_map:
                topic_map[assigned_topic_id].add_device(device, confidence)
                self.logger.debug(
                    f"Device {device.id} -> \
                        Topic {assigned_topic_id} ({confidence:.3f})"
                )

        return topics

    def group_devices(self, devices: list[Device]) -> list[Group]:
        """Group devices using BERTopic clustering.

        Args:
            devices: List of devices to group

        Returns:
            List of groups representing discovered topics
        """
        if not devices:
            self.logger.warning("No devices provided for grouping")
            return []

        if not self.embedding_model:
            self.logger.error("Embedding model not loaded")
            return []

        self.logger.info(f"Grouping {len(devices)} devices using BERTopic")

        # Extract text from devices
        documents = [self._extract_device_text(device) for device in devices]

        # Filter out empty documents
        non_empty_docs = []
        non_empty_devices = []
        for doc, device in zip(documents, devices):
            if doc.strip():
                non_empty_docs.append(doc)
                non_empty_devices.append(device)

        if not non_empty_docs:
            self.logger.warning("No valid text content found in devices")
            return []

        if len(non_empty_docs) < self.config.min_topic_size:
            self.logger.warning(
                f"Only {len(non_empty_docs)} documents available, "
                f"minimum topic size is {self.config.min_topic_size}"
            )
            return []

        self.logger.info(
            f"Processing {len(non_empty_docs)} devices with valid text content"
        )

        # Fit BERTopic model
        self.bertopic_result = self._fit_bertopic_model(non_empty_docs)

        # Create topics with names and descriptions
        topics = self._create_topics_from_bertopic()
        self.bertopic_result.topics = topics

        # Assign devices to topics
        topics_with_devices = self._assign_devices_to_topics(non_empty_devices, topics)

        # Convert to Group objects
        groups = []
        for topic in topics_with_devices:
            if topic.devices:  # Only include topics with assigned devices
                groups.append(
                    Group(
                        name=topic.name,
                        devices=topic.devices,
                        parent_classes=set(),  # BERTopic doesn't create hierarchies
                    )
                )
                self.logger.info(
                    f"Created group '{topic.name}' with {len(topic.devices)} devices"
                )

        self.logger.info(f"Created {len(groups)} topic-based groups")

        # Save analysis if configured
        if self.config.save_analysis:
            try:
                # Create timestamped directory to avoid overwrites
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = f"{self.config.analysis_output_dir}_{timestamp}"
                self.save_all_analysis(output_dir)
            except Exception as e:
                self.logger.warning(f"Failed to save topic analysis: {e}")

        return groups

    def save_all_analysis(self, output_dir: str = "bertopic_analysis") -> None:
        """Save all topic analysis files to a directory.

        Args:
            output_dir: Directory to save all analysis files
        """
        if not self.bertopic_result or not self.bertopic_result.topics:
            self.logger.warning("No topics available for analysis")
            return

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Save topic information
        self._save_topic_info(output_path / "topic_info.json")
        self._save_topic_words(output_path / "topic_words.txt")
        self._save_device_assignments(output_path / "device_assignments.txt")

        self.logger.info(f"All topic analysis saved to {output_path}/")

    def _save_topic_info(self, output_file: Path) -> None:
        """Save topic information as JSON."""
        topic_data = {}
        for topic in self.bertopic_result.topics:
            topic_data[f"topic_{topic.id}"] = {
                "name": topic.name,
                "description": topic.description,
                "keywords": topic.keywords,
                "word_scores": topic.word_scores,
                "num_devices": len(topic.devices),
                "device_ids": [device.id for device in topic.devices],
                "representative_docs": topic.representative_docs,
            }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(topic_data, f, indent=2, ensure_ascii=False)

    def _save_topic_words(self, output_file: Path) -> None:
        """Save topic words to text file."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=== BERTopic Topic Words ===\n\n")

            for topic in self.bertopic_result.topics:
                f.write(f"Topic {topic.id}: {topic.name}\n")
                f.write(f"Description: {topic.description}\n")
                f.write(f"Devices: {len(topic.devices)}\n")
                f.write("Keywords:\n")

                for keyword in topic.keywords:
                    score = topic.word_scores.get(keyword, 0.0)
                    f.write(f"  {keyword:<20} {score:.4f}\n")

                f.write("-" * 50 + "\n\n")

    def _save_device_assignments(self, output_file: Path) -> None:
        """Save device assignments to text file."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=== BERTopic Device Assignments ===\n\n")

            for topic in self.bertopic_result.topics:
                if not topic.devices:
                    continue

                f.write(f"Topic {topic.id}: {topic.name}\n")
                f.write(f"Total devices: {len(topic.devices)}\n")

                # Sort devices by confidence
                device_scores = [
                    (device, topic.confidence_scores.get(device.id, 0.0))
                    for device in topic.devices
                ]
                device_scores.sort(key=lambda x: x[1], reverse=True)

                for device, score in device_scores:
                    device_text = self._extract_device_text(device)
                    f.write(f"  {device.id:<15} {score:.3f}  {device_text}\n")

                f.write("-" * 70 + "\n\n")

    def get_topic_info(self) -> Optional[BERTopicResult]:
        """Get detailed information about discovered topics.

        Returns:
            BERTopic results with topic information, or None if not fitted
        """
        return self.bertopic_result
