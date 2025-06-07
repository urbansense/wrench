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
    def __init__(self, embedder: BaseEmbedder, threshold=0.9):
        self._embedder = embedder
        self._threshold = threshold
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

        all_sim_scores = self._calc_similarity(doc_embeddings, cluster_embeddings)

        # all docs now have a 1 for assigned topics
        classified = np.where(all_sim_scores > self._threshold, 1, 0)

        unclassified_docs = np.where(~classified.any(axis=1))[0]

        if unclassified_docs.shape[0] != 0:
            self._logger.warning(
                "documents %s were not classified successfully",
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

        row_min = similarity_matrix.min(axis=1).reshape(-1, 1)
        row_max = similarity_matrix.max(axis=1).reshape(-1, 1)
        normalized_similarity = (similarity_matrix - row_min) / (row_max - row_min)

        return normalized_similarity
