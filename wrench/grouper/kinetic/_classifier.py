import json
import os

import numpy as np

from wrench.grouper.kinetic.embedder import BaseEmbedder
from wrench.log import logger as wrench_logger
from wrench.utils.prompt_manager import PromptManager

from .defaults import (
    CACHE_DIR,
    OUTLIER_IQR_MULTIPLIER,
    OUTLIER_PERCENTILE_HIGH,
    OUTLIER_PERCENTILE_LOW,
    SIMILARITY_TEMPERATURE,
)
from .models import Cluster

_CLUSTER_PROMPT = PromptManager.get_prompt("embed_topics.txt")
_DOC_PROMPT = PromptManager.get_prompt("embed_documents.txt")


class Classifier:
    def __init__(
        self,
        embedder: BaseEmbedder,
    ):
        self._embedder = embedder
        self._logger = wrench_logger.getChild(self.__class__.__name__)
        self.doc_embeddings: np.ndarray | None = None

        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_clusters = self.cache_dir / "clusters.json"
        self.cache_embeddings = self.cache_dir / "cluster_embeddings.npz"

    def _embed_clusters(self, cluster_kws: list[list[str]]) -> np.ndarray:
        # embeddings shape is [num_clusters, D]
        return self._embedder.embed(
            [str(kws) for kws in cluster_kws],
            prompt=_CLUSTER_PROMPT,
        )

    def is_cached(self) -> bool:
        return os.path.isfile(self.cache_clusters) and os.path.isfile(
            self.cache_embeddings
        )

    def _embed_docs(self, documents: list[str]) -> np.ndarray:
        return self._embedder.embed(documents, prompt=_DOC_PROMPT)

    def _load_clusters(self) -> list[Cluster]:
        with open(self.cache_clusters, "r") as f:
            clusters: dict = json.load(f)

        return [Cluster.model_validate(c) for c in clusters]

    def _load_embeddings(self) -> np.ndarray:
        data = np.load(self.cache_embeddings)

        return data["embeddings"]

    def _save_clusters(self, clusters: list[Cluster], embeddings: np.ndarray):
        np.savez_compressed(self.cache_embeddings, embeddings=embeddings)

        with open(self.cache_clusters, "w") as f:
            json.dump([c.model_dump(mode="json") for c in clusters], f)

    def classify(
        self,
        docs: list[str],
        clusters: list[Cluster] | None = None,
    ) -> list[np.ndarray]:
        """
        Classifies documents against a list of topics.

        Args:
            docs: A list of document strings to classify.
            topic_tree: The topic tree containing hierarchical structure of the topics
                to be classified. If None, attempts to use cached topics.
            clusters: A dict of clusters with the cluster keywords.

        Returns:
            A list of integer arrays representing the document index classified to
            each topic.

        """
        cluster_embeddings = self._check_cache(clusters)

        doc_embeddings = self._embed_docs(docs)
        self.doc_embeddings = doc_embeddings

        all_sim_scores = self._calc_similarity(doc_embeddings, cluster_embeddings)
        scaled_scores = self._apply_temperature_softmax(all_sim_scores)

        # Store per-document scores for experiment tracking
        self.embedding_sim_scores = scaled_scores
        self.substring_sim_scores = np.zeros_like(scaled_scores)
        self.combined_sim_scores = scaled_scores

        # Raw cosine scores for outlier detection (IQR is calibrated for [-1, 1] space)
        # Scaled scores for argmax (better discrimination between similar clusters)
        max_scores = np.max(all_sim_scores, axis=1)
        max_indices = np.argmax(scaled_scores, axis=1)

        # detect outliers using IQR method
        q1 = np.percentile(max_scores, OUTLIER_PERCENTILE_LOW)
        q3 = np.percentile(max_scores, OUTLIER_PERCENTILE_HIGH)
        iqr = q3 - q1
        lower_bound = q1 - OUTLIER_IQR_MULTIPLIER * iqr

        # classify documents that are not statistical outliers
        is_inlier = max_scores >= lower_bound
        classified = np.zeros_like(all_sim_scores, dtype=int)
        classified[is_inlier, max_indices[is_inlier]] = 1

        unclassified_docs = np.where(~classified.any(axis=1))[0]

        if unclassified_docs.shape[0] > 0:
            self._logger.info(
                "%d documents identified as outliers (similarity below %.3f)",
                len(unclassified_docs),
                lower_bound,
            )
            self._logger.debug(
                "Outlier documents: %s",
                [docs[i] for i in unclassified_docs],
            )

        # transpose to get topic-to-docs
        transposed = classified.T
        # get doc indexes for each topic
        result = [np.nonzero(row)[0] for row in transposed]

        if len(clusters) != len(result):
            raise AttributeError(
                "length of clusters is different from resulting embeddings"
            )

        return result

    def _check_cache(self, clusters: list[Cluster]) -> np.ndarray:
        if self.is_cached():
            clusters = self._load_clusters()
            embeddings = self._load_embeddings()

            return embeddings

        cluster_embeddings = self._embed_clusters([c.keywords for c in clusters])
        self._save_clusters(clusters, cluster_embeddings)
        return cluster_embeddings

    def _apply_temperature_softmax(self, scores: np.ndarray) -> np.ndarray:
        """Apply temperature-scaled softmax to a similarity matrix.

        Amplifies small differences between cosine similarity scores, which tend
        to saturate near 1.0 for L2-normalized embeddings in high dimensions.

        Args:
            scores: Similarity matrix of shape (n_docs, n_clusters).

        Returns:
            Softmax-scaled scores of same shape, each row summing to 1.
        """
        scaled = scores / SIMILARITY_TEMPERATURE
        # Subtract row max for numerical stability before exp
        shifted = scaled - scaled.max(axis=1, keepdims=True)
        exp_scores = np.exp(shifted)
        return exp_scores / exp_scores.sum(axis=1, keepdims=True)

    def _calc_similarity(
        self, doc_embeddings: np.ndarray, cluster_embeddings: np.ndarray
    ) -> np.ndarray:
        # Ensure doc_embeddings is 2D, even if a single embedding (1D) was passed
        if doc_embeddings.ndim == 1:
            doc_embeddings = np.atleast_2d(doc_embeddings)

        num_docs = doc_embeddings.shape[0]
        num_clusters = cluster_embeddings.shape[0]
        self._logger.info(
            "Calculating similarity for %s documents, with %s clusters",
            num_docs,
            num_clusters,
        )

        similarity_matrix = self._embedder.similarity(
            doc_embeddings, cluster_embeddings
        )
        # similarity_matrix shape (n_doc, n_cluster)

        return similarity_matrix
