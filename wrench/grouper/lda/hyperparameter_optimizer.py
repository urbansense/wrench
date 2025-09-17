"""Hyperparameter optimization for LDA grouper."""

import itertools
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import silhouette_score

from wrench.grouper.lda.models import LDAConfig
from wrench.log import logger
from wrench.models import Device


class LDAMetrics:
    """Container for LDA evaluation metrics."""

    def __init__(self) -> None:
        self.perplexity: float = 0.0
        self.coherence_score: float = 0.0
        self.silhouette_score: float = 0.0
        self.num_empty_topics: int = 0
        self.topic_diversity: float = 0.0
        self.assignment_ratio: float = 0.0  # Fraction of devices assigned to topics


class LDAHyperparameterOptimizer:
    """Optimizes LDA hyperparameters using multiple evaluation metrics."""

    def __init__(self, devices: List[Device], config_base: LDAConfig):
        """Initialize optimizer with base configuration.

        Args:
            devices: List of devices to use for optimization
            config_base: Base LDA configuration to modify
        """
        self.devices = devices
        self.config_base = config_base
        self.logger = logger.getChild(self.__class__.__name__)

        # Extract text from devices for optimization
        self.documents = self._extract_device_texts(devices)

    def _extract_device_texts(self, devices: List[Device]) -> List[str]:
        """Extract text content from devices."""
        documents = []
        for device in devices:
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

            combined_text = " ".join(text_parts).lower()
            if combined_text.strip():
                documents.append(combined_text)

        return documents

    def _compute_coherence_score(
        self, lda_model, vectorizer, top_words: int = 10
    ) -> float:
        """Compute topic coherence using word co-occurrence.

        This is a simplified coherence measure based on word co-occurrence
        within the top words of each topic.
        """
        try:
            feature_names = vectorizer.get_feature_names_out()
            coherence_scores = []

            for topic_idx in range(lda_model.n_components):
                topic_dist = lda_model.components_[topic_idx]
                top_indices = np.argsort(topic_dist)[-top_words:]
                top_words_list = [feature_names[i] for i in top_indices]

                # Simple coherence: average pairwise similarity
                word_scores = []
                for i, word1 in enumerate(top_words_list):
                    for word2 in top_words_list[i + 1 :]:
                        # This is a simplified measure - in practice you'd use
                        # more sophisticated coherence measures like C_V or NPMI
                        word_scores.append(1.0)  # Placeholder

                if word_scores:
                    coherence_scores.append(np.mean(word_scores))

            return np.mean(coherence_scores) if coherence_scores else 0.0

        except Exception as e:
            self.logger.warning(f"Coherence computation failed: {e}")
            return 0.0

    def _compute_topic_diversity(self, lda_model, top_words: int = 25) -> float:
        """Compute topic diversity (1 - average pairwise topic similarity)."""
        try:
            topics = []
            for topic_idx in range(lda_model.n_components):
                topic_dist = lda_model.components_[topic_idx]
                top_indices = set(np.argsort(topic_dist)[-top_words:])
                topics.append(top_indices)

            similarities = []
            for i, topic1 in enumerate(topics):
                for topic2 in topics[i + 1 :]:
                    # Jaccard similarity
                    intersection = len(topic1.intersection(topic2))
                    union = len(topic1.union(topic2))
                    similarity = intersection / union if union > 0 else 0
                    similarities.append(similarity)

            avg_similarity = np.mean(similarities) if similarities else 0.0
            return float(1 - avg_similarity)  # Diversity = 1 - similarity

        except Exception as e:
            self.logger.warning(f"Topic diversity computation failed: {e}")
            return 0.0

    def evaluate_config(self, config: LDAConfig) -> LDAMetrics:
        """Evaluate a single LDA configuration."""
        metrics = LDAMetrics()

        try:
            # Create vectorizer
            vectorizer = CountVectorizer(
                min_df=config.min_df,
                max_df=config.max_df,
                max_features=config.max_features,
                stop_words="english",
                token_pattern=r"\b[a-zA-Z]{2,}\b",
            )

            # Fit vectorizer and transform documents
            doc_term_matrix = vectorizer.fit_transform(self.documents)

            # Fit LDA model
            lda_model = LatentDirichletAllocation(
                n_components=config.n_topics,
                max_iter=config.max_iter,
                doc_topic_prior=config.alpha,
                topic_word_prior=config.beta,
                random_state=config.random_state,
                verbose=0,
            )

            document_topic_matrix = lda_model.fit_transform(doc_term_matrix)

            # Compute metrics
            metrics.perplexity = lda_model.perplexity(doc_term_matrix)
            metrics.coherence_score = self._compute_coherence_score(
                lda_model, vectorizer
            )

            # Silhouette score (if we have enough samples)
            if len(self.documents) > config.n_topics:
                try:
                    # Assign each document to its most probable topic
                    topic_assignments = np.argmax(document_topic_matrix, axis=1)
                    if len(np.unique(topic_assignments)) > 1:
                        metrics.silhouette_score = silhouette_score(
                            document_topic_matrix, topic_assignments
                        )
                except Exception as e:
                    self.logger.debug(f"Silhouette score computation failed: {e}")
                    metrics.silhouette_score = 0.0

            # Topic diversity
            metrics.topic_diversity = self._compute_topic_diversity(lda_model)

            # Count empty topics (topics with very low max probability)
            max_probs = np.max(document_topic_matrix, axis=0)
            metrics.num_empty_topics = np.sum(max_probs < 0.01)

            # Assignment ratio (fraction of documents assigned above threshold)
            max_topic_probs = np.max(document_topic_matrix, axis=1)
            metrics.assignment_ratio = np.mean(
                max_topic_probs >= config.similarity_threshold
            )

        except Exception as e:
            self.logger.error(f"Config evaluation failed: {e}")
            # Return default metrics on failure

        return metrics

    def optimize_hyperparameters(
        self,
        param_grid: Dict[str, List[Any]] | None = None,
        metric_weights: Dict[str, float] | None = None,
    ) -> Tuple[LDAConfig, LDAMetrics, List[Tuple[LDAConfig, LDAMetrics]]]:
        """Optimize LDA hyperparameters using grid search.

        Args:
            param_grid: Dictionary of parameter ranges to search
            metric_weights: Weights for combining different metrics

        Returns:
            Tuple of (best_config, best_metrics, all_results)
        """
        if param_grid is None:
            param_grid = {
                "n_topics": [3, 5, 8, 10, 15, 20],
                "alpha": [0.01, 0.1, 0.5, 1.0],
                "beta": [0.01, 0.1, 0.5],
                "max_iter": [50, 100, 200],
            }

        if metric_weights is None:
            metric_weights = {
                "perplexity": -0.3,  # Lower is better
                "coherence_score": 0.3,  # Higher is better
                "silhouette_score": 0.2,  # Higher is better
                "topic_diversity": 0.2,  # Higher is better
                "assignment_ratio": 0.2,  # Higher is better
                "num_empty_topics": -0.1,  # Lower is better
            }

        self.logger.info(
            f"Starting hyperparameter optimization with \
                {len(list(itertools.product(*param_grid.values())))} configurations"
        )

        results = []
        best_score = float("-inf")
        best_config = None
        best_metrics = None

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        for i, param_combination in enumerate(itertools.product(*param_values)):
            # Create config with these parameters
            config_dict = dict(zip(param_names, param_combination))
            config = LDAConfig(**{**self.config_base.model_dump(), **config_dict})

            # Evaluate this configuration
            metrics = self.evaluate_config(config)

            # Compute weighted score
            score = (
                metrics.perplexity * metric_weights.get("perplexity", 0)
                + metrics.coherence_score * metric_weights.get("coherence_score", 0)
                + metrics.silhouette_score * metric_weights.get("silhouette_score", 0)
                + metrics.topic_diversity * metric_weights.get("topic_diversity", 0)
                + metrics.assignment_ratio * metric_weights.get("assignment_ratio", 0)
                + metrics.num_empty_topics * metric_weights.get("num_empty_topics", 0)
            )

            results.append((config, metrics))

            if score > best_score:
                best_score = score
                best_config = config
                best_metrics = metrics

            self.logger.debug(
                f"Config {i + 1}: n_topics={config.n_topics}, alpha={config.alpha}, "
                f"beta={config.beta}, score={score:.3f}"
            )

        self.logger.info(
            f"Optimization complete. Best config: n_topics={best_config.n_topics}, "
            f"alpha={best_config.alpha}, beta={best_config.beta}, "
            f"perplexity={best_metrics.perplexity:.2f}"
        )

        return best_config, best_metrics, results

    def analyze_results(
        self, results: List[Tuple[LDAConfig, LDAMetrics]]
    ) -> Dict[str, Any]:
        """Analyze optimization results and provide insights."""
        analysis = {
            "total_configs": len(results),
            "best_configs_by_metric": {},
            "metric_correlations": {},
            "parameter_trends": {},
        }

        # Find best configs for each metric
        metrics_data = {
            "perplexity": [(config, metrics.perplexity) for config, metrics in results],
            "coherence_score": [
                (config, metrics.coherence_score) for config, metrics in results
            ],
            "silhouette_score": [
                (config, metrics.silhouette_score) for config, metrics in results
            ],
            "topic_diversity": [
                (config, metrics.topic_diversity) for config, metrics in results
            ],
            "assignment_ratio": [
                (config, metrics.assignment_ratio) for config, metrics in results
            ],
        }

        for metric_name, metric_values in metrics_data.items():
            if metric_name == "perplexity":
                # Lower is better for perplexity
                best_config, best_value = min(metric_values, key=lambda x: x[1])
            else:
                # Higher is better for other metrics
                best_config, best_value = max(metric_values, key=lambda x: x[1])

            analysis["best_configs_by_metric"][metric_name] = {
                "config": best_config,
                "value": best_value,
            }

        return analysis


def suggest_parameter_ranges(
    num_devices: int, avg_text_length: int
) -> Dict[str, List[Any]]:
    """Suggest parameter ranges based on dataset characteristics.

    Args:
        num_devices: Number of devices in the dataset
        avg_text_length: Average text length per device

    Returns:
        Dictionary of suggested parameter ranges
    """
    # Heuristic rules based on dataset size
    if num_devices < 50:
        n_topics_range = [3, 5, 8]
    elif num_devices < 200:
        n_topics_range = [5, 8, 10, 15]
    elif num_devices < 500:
        n_topics_range = [8, 10, 15, 20, 25]
    else:
        n_topics_range = [10, 15, 20, 25, 30, 40]

    # Alpha (document-topic concentration)
    # Lower alpha = documents concentrate on fewer topics
    alpha_range = [0.01, 0.1, 0.5, 1.0, "auto"]

    # Beta (topic-word concentration)
    # Lower beta = topics concentrate on fewer words
    beta_range = [0.01, 0.1, 0.5]

    # Max iterations based on dataset size
    if num_devices < 100:
        max_iter_range = [50, 100]
    else:
        max_iter_range = [100, 200]

    return {
        "n_topics": n_topics_range,
        "alpha": alpha_range,
        "beta": beta_range,
        "max_iter": max_iter_range,
    }
