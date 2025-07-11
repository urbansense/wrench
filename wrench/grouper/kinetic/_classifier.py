import json
import os
from pathlib import Path

import numpy as np

from wrench.grouper.kinetic.embedder import BaseEmbedder
from wrench.log import logger as wrench_logger
from wrench.utils.prompt_manager import PromptManager

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

        self.cache_dir = Path(".kineticache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_clusters = self.cache_dir / "clusters.json"
        self.cache_embeddings = self.cache_dir / "embeddings.npz"

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

        # Calculate both embedding and substring similarities
        embedding_sim_scores = self._calc_similarity(doc_embeddings, cluster_embeddings)
        substring_sim_scores = self._calc_substring_similarity(docs, clusters)

        # Combine similarities using root mean square
        all_sim_scores = np.sqrt(
            (embedding_sim_scores**2 + substring_sim_scores**2) / 2
        )

        max_scores = np.max(all_sim_scores, axis=1)
        max_indices = np.argmax(all_sim_scores, axis=1)

        # detect outliers using IQR method
        q1 = np.percentile(max_scores, 10)
        q3 = np.percentile(max_scores, 90)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr

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

    def _calc_substring_similarity(
        self, docs: list[str], clusters: list[Cluster]
    ) -> np.ndarray:
        """Calculate substring matching similarity using vectorized numpy operations."""
        num_docs = len(docs)
        num_clusters = len(clusters)

        # Convert documents to lowercase numpy array
        docs_lower = np.array([doc.lower() for doc in docs])

        # Initialize similarity matrix
        substring_matrix = np.zeros((num_docs, num_clusters))

        for cluster_idx, cluster in enumerate(clusters):
            cluster_keywords = [kw.lower() for kw in cluster.keywords]

            # Sum keyword matches across all keywords in cluster
            keyword_matches = np.zeros(num_docs)

            for keyword in cluster_keywords:
                # Vectorized count occurrences for frequency weighting
                keyword_counts = np.array([doc.count(keyword) for doc in docs_lower])
                keyword_matches += keyword_counts

            # Normalize by number of keywords in cluster
            substring_matrix[:, cluster_idx] = keyword_matches / len(cluster_keywords)

        return substring_matrix

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
