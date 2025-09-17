import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import validate_call
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

from wrench.grouper.base import BaseGrouper
from wrench.log import logger
from wrench.models import Device, Group
from wrench.utils.config import LLMConfig

from .hyperparameter_optimizer import (
    LDAHyperparameterOptimizer,
    suggest_parameter_ranges,
)
from .models import LDAConfig, LDAResult, LDATopic, OptimizationConfig
from .topic_namer import create_topic_namer


class LDAGrouper(BaseGrouper):
    """LDA-based grouper for discovering topics and grouping devices.

    This grouper uses Latent Dirichlet Allocation (LDA) to discover topics from
    device descriptions and metadata, then assigns devices to topics based on
    similarity calculations.
    """

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        config: LDAConfig,
        llm_config: Optional[LLMConfig] = None,
        optimization: Optional[OptimizationConfig] = None,
    ):
        """Initialize LDA grouper.

        Args:
            config: LDA configuration
            llm_config: LLM configuration for topic naming (optional)
            optimization: Optimization configuration (optional)
        """
        self.config = config
        self.llm_config = llm_config
        self.optimization = optimization
        self.logger = logger.getChild(self.__class__.__name__)

        # Initialize components
        self.vectorizer: Optional[CountVectorizer] = None
        self.lda_model: Optional[LatentDirichletAllocation] = None
        self.lda_result: Optional[LDAResult] = None
        self._optimized_config: Optional[LDAConfig] = None

        # Create topic namer
        self.topic_namer = create_topic_namer(
            use_llm=config.use_llm_naming and llm_config is not None,
            llm_config=llm_config,
            temperature=0.1,
        )

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for LDA modeling.

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

    def _fit_lda_model(self, documents: list[str]) -> LDAResult:
        """Fit LDA model on documents.

        Args:
            documents: List of document texts

        Returns:
            LDA modeling results
        """
        self.logger.info(
            f"Fitting LDA model with {self.config.n_topics} topics "
            f"on {len(documents)} documents"
        )

        # Create vectorizer
        self.vectorizer = CountVectorizer(
            min_df=self.config.min_df,
            max_df=self.config.max_df,
            max_features=self.config.max_features,
            stop_words="english",
            token_pattern=r"\b[a-zA-Z]{2,}\b",  # Only words with 2+ letters
        )

        # Fit vectorizer and transform documents
        doc_term_matrix = self.vectorizer.fit_transform(documents)
        feature_names = self.vectorizer.get_feature_names_out()

        # Fit LDA model
        self.lda_model = LatentDirichletAllocation(
            n_components=self.config.n_topics,
            max_iter=self.config.max_iter,
            doc_topic_prior=self.config.alpha,
            topic_word_prior=self.config.beta,
            random_state=self.config.random_state,
            verbose=0,
        )

        document_topic_matrix = self.lda_model.fit_transform(doc_term_matrix)

        # Calculate perplexity
        perplexity = self.lda_model.perplexity(doc_term_matrix)

        self.logger.info(f"LDA model fitted. Perplexity: {perplexity:.2f}")

        return LDAResult(
            topics=[],  # Will be populated later
            document_topic_matrix=document_topic_matrix,
            feature_names=(
                feature_names.tolist()
                if hasattr(feature_names, "tolist")
                else list(feature_names)
            ),
            perplexity=perplexity,
        )

    def _extract_topic_keywords(
        self, topic_idx: int, n_words: int = None
    ) -> tuple[list[str], dict[str, float]]:
        """Extract top keywords for a topic.

        Args:
            topic_idx: Topic index
            n_words: Number of top words to extract

        Returns:
            Tuple of (keywords_list, word_distribution_dict)
        """
        if n_words is None:
            n_words = self.config.top_words

        topic_dist = self.lda_model.components_[topic_idx]
        feature_names = self.lda_result.feature_names

        # Get top word indices
        top_indices = np.argsort(topic_dist)[-n_words:][::-1]

        # Extract keywords and their probabilities
        keywords = []
        word_distribution = {}

        for idx in top_indices:
            word = feature_names[idx]
            prob = topic_dist[idx]
            keywords.append(word)
            word_distribution[word] = float(prob)

        return keywords, word_distribution

    def _create_topics_from_lda(self) -> list[LDATopic]:
        """Create LDATopic objects from fitted LDA model.

        Returns:
            List of LDA topics with names and descriptions
        """
        # First, extract all topics data
        topics_data = []
        for topic_idx in range(self.config.n_topics):
            keywords, word_distribution = self._extract_topic_keywords(topic_idx)
            topics_data.append(
                {
                    "id": topic_idx,
                    "keywords": keywords,
                    "word_distribution": word_distribution,
                }
            )

        # Generate consolidated topic names and descriptions
        consolidated_topics = self.topic_namer.name_topics(topics_data)

        # Create LDATopic objects from consolidated results
        topics = []
        topic_id_counter = 0

        for consolidated in consolidated_topics:
            # Get keywords and word distribution from the first original topic
            # for merged topics, we could combine them, but for simplicity use the first
            original_id = consolidated["original_topic_ids"][0]
            original_data = topics_data[original_id]

            topic = LDATopic(
                id=topic_id_counter,
                name=consolidated["name"],
                description=consolidated["description"],
                keywords=original_data["keywords"],
                word_distribution=original_data["word_distribution"],
                original_topic_ids=consolidated["original_topic_ids"],
            )

            topics.append(topic)
            self.logger.debug(
                f"Topic {topic_id_counter}: \
                    {consolidated['name']} (from {consolidated['original_topic_ids']})"
            )
            topic_id_counter += 1

        return topics

    def _assign_devices_to_topics(
        self, devices: list[Device], topics: list[LDATopic]
    ) -> list[LDATopic]:
        """Assign devices to topics based on similarity.

        Args:
            devices: List of devices to assign
            topics: List of topics to assign to

        Returns:
            Topics with assigned devices
        """
        document_topic_matrix = self.lda_result.document_topic_matrix

        for device_idx, device in enumerate(devices):
            # Get topic probabilities for this device
            topic_probs = document_topic_matrix[device_idx]

            # Find the best consolidated topic for this device
            best_topic = None
            best_prob = 0.0

            for topic in topics:
                # Calculate max probability among original topics
                max_prob = max(
                    topic_probs[orig_id] for orig_id in topic.original_topic_ids
                )

                if (
                    max_prob >= self.config.similarity_threshold
                    and max_prob > best_prob
                ):
                    best_topic = topic
                    best_prob = max_prob

            if best_topic:
                best_topic.add_device(device, best_prob)
                self.logger.debug(
                    f"Device {device.id} -> {best_topic.name} ({best_prob:.3f})"
                )

        return topics

    def _optimize_hyperparameters_if_needed(self, devices: list[Device]) -> None:
        """Run hyperparameter optimization if configured."""
        if (
            self.optimization
            and self.optimization.enabled
            and self._optimized_config is None
        ):
            self.logger.info("Running hyperparameter optimization...")

            # Use configured param_grid or generate smart defaults
            param_grid = self.optimization.param_grid
            if not param_grid:
                texts = [self._extract_device_text(device) for device in devices]
                avg_text_length = sum(len(text.split()) for text in texts) / len(texts)
                param_grid = suggest_parameter_ranges(
                    len(devices), int(avg_text_length)
                )

            # Use configured metric_weights or defaults
            metric_weights = self.optimization.metric_weights or None

            # Run optimization
            optimizer = LDAHyperparameterOptimizer(devices, self.config)
            best_config, best_metrics, all_results = optimizer.optimize_hyperparameters(
                param_grid, metric_weights
            )

            # Store optimized config and update current config
            self._optimized_config = best_config
            self.config = best_config

            self.logger.info(
                f"Optimization complete. Using optimized config: "
                f"n_topics={best_config.n_topics}, alpha={best_config.alpha}, "
                f"beta={best_config.beta}, perplexity={best_metrics.perplexity:.2f}"
            )

    def group_devices(self, devices: list[Device]) -> list[Group]:
        """Group devices using LDA topic modeling.

        Args:
            devices: List of devices to group

        Returns:
            List of groups representing discovered topics
        """
        if not devices:
            self.logger.warning("No devices provided for grouping")
            return []

        # Run hyperparameter optimization if configured
        self._optimize_hyperparameters_if_needed(devices)

        self.logger.info(f"Grouping {len(devices)} devices using LDA")

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

        self.logger.info(
            f"Processing {len(non_empty_docs)} devices with valid text content"
        )

        # Fit LDA model
        self.lda_result = self._fit_lda_model(non_empty_docs)

        # Create topics with names and descriptions
        topics = self._create_topics_from_lda()
        self.lda_result.topics = topics

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
                        parent_classes=set(),  # LDA doesn't create hierarchies
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

    def predict_topic_for_text(self, text: str) -> dict[str, float]:
        """Predict topic probabilities for new text.

        Args:
            text: Text to classify

        Returns:
            Dictionary mapping topic names to probabilities
        """
        if self.vectorizer is None or self.lda_model is None:
            raise ValueError("Model not fitted. Call group_devices() first.")

        # Preprocess and vectorize text
        processed_text = self._preprocess_text(text)
        text_vector = self.vectorizer.transform([processed_text])

        # Get topic probabilities
        topic_probs = self.lda_model.transform(text_vector)[0]

        # Map to consolidated topic names
        topic_predictions = {}
        for topic in self.lda_result.topics:
            # Calculate max probability among original topics
            max_prob = max(
                topic_probs[orig_id]
                for orig_id in topic.original_topic_ids
                if orig_id < len(topic_probs)
            )
            topic_predictions[topic.name] = float(max_prob)

        return topic_predictions

    def get_topic_word_distributions(self) -> dict[str, dict[str, float]]:
        """Get word distributions for all topics.

        Returns:
            Dictionary mapping topic names to their word distributions
        """
        if self.lda_result is None or not self.lda_result.topics:
            self.logger.warning("No topics available. Run group_devices() first.")
            return {}

        distributions = {}
        for topic in self.lda_result.topics:
            distributions[topic.name] = topic.word_distribution

        return distributions

    def save_topic_words(
        self, output_file: str = "topic_words.txt", top_n: int = 20
    ) -> None:
        """Save top words for each topic with their probabilities to a file.

        Args:
            output_file: Path to output file
            top_n: Number of top words to save per topic
        """
        if self.lda_result is None or not self.lda_result.topics:
            self.logger.warning("No topics available. Run group_devices() first.")
            return

        output_path = Path(output_file)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"=== Topic Word Distributions (Top {top_n} words) ===\n\n")

            for topic in self.lda_result.topics:
                f.write(f"Topic: {topic.name}\n")
                f.write(f"Description: {topic.description}\n")
                f.write(f"Devices assigned: {len(topic.devices)}\n")
                f.write(f"Original LDA topic IDs: {topic.original_topic_ids}\n")
                f.write("Top words:\n")

                # Sort words by probability
                sorted_words = sorted(
                    topic.word_distribution.items(), key=lambda x: x[1], reverse=True
                )[:top_n]

                for word, prob in sorted_words:
                    f.write(f"  {word:<20} {prob:.4f}\n")

                f.write("-" * 50 + "\n\n")

        self.logger.info(f"Topic word distributions saved to {output_path}")

    def save_topic_words_json(self, output_file: str = "topic_words.json") -> None:
        """Save topic word distributions as JSON for programmatic access.

        Args:
            output_file: Path to output JSON file
        """
        if self.lda_result is None or not self.lda_result.topics:
            self.logger.warning("No topics available. Run group_devices() first.")
            return

        output_path = Path(output_file)

        topic_data = {}
        for topic in self.lda_result.topics:
            topic_data[topic.name] = {
                "description": topic.description,
                "num_devices": len(topic.devices),
                "original_topic_ids": topic.original_topic_ids,
                "keywords": topic.keywords,
                "word_distribution": topic.word_distribution,
                "device_ids": [device.id for device in topic.devices],
            }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(topic_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Topic data saved as JSON to {output_path}")

    def save_topic_devices(
        self, output_file: str = "topic_devices.txt", top_n: int = 10
    ) -> None:
        """Save top devices for each topic with their confidence scores to a file.

        Args:
            output_file: Path to output file
            top_n: Number of top devices to save per topic
        """
        if self.lda_result is None or not self.lda_result.topics:
            self.logger.warning("No topics available. Run group_devices() first.")
            return

        output_path = Path(output_file)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"=== Topic Device Assignments (Top {top_n} devices) ===\n\n")

            for topic in self.lda_result.topics:
                f.write(f"Topic: {topic.name}\n")
                f.write(f"Description: {topic.description}\n")
                f.write(f"Total devices: {len(topic.devices)}\n")
                f.write(f"Original LDA topic IDs: {topic.original_topic_ids}\n")

                if not topic.devices:
                    f.write("  No devices assigned to this topic\n")
                    f.write("-" * 50 + "\n\n")
                    continue

                # Sort devices by confidence score
                device_scores = [
                    (device, topic.confidence_scores.get(device.id, 0.0))
                    for device in topic.devices
                ]
                device_scores.sort(key=lambda x: x[1], reverse=True)

                f.write("Top devices:\n")
                for device, score in device_scores[:top_n]:
                    device_text = self._extract_device_text(device)
                    f.write(f"  {device.id:<15} {score:.3f}  {device_text}\n")

                f.write("-" * 70 + "\n\n")

        self.logger.info(f"Topic device assignments saved to {output_path}")

    def analyze_topic_quality(self) -> dict:
        """Analyze the quality and characteristics of discovered topics.

        Returns:
            Dictionary with topic analysis
        """
        if self.lda_result is None or not self.lda_result.topics:
            self.logger.warning("No topics available. Run group_devices() first.")
            return {}

        analysis = {
            "total_topics": len(self.lda_result.topics),
            "total_devices_assigned": sum(
                len(topic.devices) for topic in self.lda_result.topics
            ),
            "topics_with_devices": sum(
                1 for topic in self.lda_result.topics if topic.devices
            ),
            "average_devices_per_topic": 0,
            "topic_details": [],
        }

        if analysis["topics_with_devices"] > 0:
            analysis["average_devices_per_topic"] = (
                analysis["total_devices_assigned"] / analysis["topics_with_devices"]
            )

        for topic in self.lda_result.topics:
            if not topic.devices:
                continue

            confidence_scores = [
                topic.confidence_scores.get(device.id, 0.0) for device in topic.devices
            ]

            topic_detail = {
                "name": topic.name,
                "description": topic.description,
                "num_devices": len(topic.devices),
                "avg_confidence": sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0,
                "min_confidence": min(confidence_scores) if confidence_scores else 0,
                "max_confidence": max(confidence_scores) if confidence_scores else 0,
                "top_words": list(topic.keywords[:5]),  # Top 5 keywords
                "original_topic_ids": topic.original_topic_ids,
            }
            analysis["topic_details"].append(topic_detail)

        return analysis

    def save_topic_analysis(self, output_file: str = "topic_analysis.json") -> None:
        """Save comprehensive topic analysis to a JSON file.

        Args:
            output_file: Path to output JSON file
        """
        if self.lda_result is None or not self.lda_result.topics:
            self.logger.warning("No topics available. Run group_devices() first.")
            return

        output_path = Path(output_file)

        # Get comprehensive analysis
        analysis = self.analyze_topic_quality()

        # Add additional information
        analysis["lda_config"] = self.config.model_dump()
        analysis["model_perplexity"] = (
            self.lda_result.perplexity if self.lda_result else None
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Topic analysis saved to {output_path}")

    def save_all_analysis(self, output_dir: str = "lda_analysis") -> None:
        """Save all topic analysis files to a directory.

        Args:
            output_dir: Directory to save all analysis files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Save all analysis files
        self.save_topic_words(output_path / "topic_words.txt")
        self.save_topic_words_json(output_path / "topic_words.json")
        self.save_topic_devices(output_path / "topic_devices.txt")
        self.save_topic_analysis(output_path / "topic_analysis.json")

        self.logger.info(f"All topic analysis saved to {output_path}/")

    def get_topic_info(self) -> Optional[LDAResult]:
        """Get detailed information about discovered topics.

        Returns:
            LDA results with topic information, or None if not fitted
        """
        return self.lda_result

    @staticmethod
    def _extract_text_static(device: Device) -> str:
        """Static version of text extraction for optimization."""
        text_parts = []

        if device.name:
            text_parts.append(device.name)
        if device.description:
            text_parts.append(device.description)
        if device.datastreams:
            text_parts.extend(device.datastreams)
        if device.sensors:
            text_parts.extend(device.sensors)
        if device.observed_properties:
            text_parts.extend(device.observed_properties)

        return " ".join(text_parts).lower()
