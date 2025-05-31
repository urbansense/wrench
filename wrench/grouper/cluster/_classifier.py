import json
import os
from pathlib import Path

import numpy as np

from wrench.grouper.cluster.embedder import BaseEmbedder
from wrench.log import logger as wrench_logger
from wrench.utils.prompt_manager import PromptManager

from .llm_topic_generator import Topic, TopicTree

_TOPIC_PROMPT = PromptManager.get_prompt("embed_topics.txt")
_DOC_PROMPT = PromptManager.get_prompt("embed_documents.txt")


class Classifier:
    def __init__(self, embedder: BaseEmbedder, threshold=0.9):
        self._embedder = embedder
        self._threshold = threshold
        self._logger = wrench_logger.getChild(self.__class__.__name__)

        self.cache_dir = Path(".kineticache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_topics = self.cache_dir / "topics.json"
        self.cache_embeddings = self.cache_dir / "embeddings.npz"

    def _embed_topics(self, topics: list[Topic]) -> np.ndarray:
        # embeddings shape is [num_topics, D]
        return self._embedder.embed(
            [
                "{name}; {keywords}".format(
                    name=topic.name, keywords=",".join(topic.keywords)
                )
                for topic in topics
            ],
            prompt=_TOPIC_PROMPT,
        )

    def is_cached(self) -> bool:
        return os.path.isfile(self.cache_topics) and os.path.isfile(
            self.cache_embeddings
        )

    def _embed_docs(self, documents: list[str]) -> np.ndarray:
        return self._embedder.embed(documents, prompt=_DOC_PROMPT)

    def _load_topics(self) -> tuple[TopicTree, np.ndarray]:
        with open(self.cache_topics, "r") as f:
            tree: dict = json.load(f)

        topic_tree = TopicTree.model_validate(tree)

        data = np.load(self.cache_embeddings)

        return topic_tree, data["embeddings"]

    def _save_topics(self, topic_tree: TopicTree, embeddings: np.ndarray):
        np.savez_compressed(self.cache_embeddings, embeddings)

        with open(self.cache_topics, "w") as f:
            json.dump(topic_tree.model_dump(mode="json"), f)

    def classify(
        self,
        docs: list[str],
        topic_tree: TopicTree | None = None,
    ) -> dict[Topic, np.ndarray]:
        """
        Classifies documents against a list of topics.

        Args:
            docs: A list of document strings to classify.
            topic_tree: The topic tree containing hierarchical structure of the topics
                to be classified. If None, attempts to use cached topics.

        Returns:
            A list of integer arrays representing the document index classified to
            each topic.

        """
        all_topics, topic_embeddings = self._check_cache(topic_tree)

        doc_embeddings = self._embed_docs(docs)

        all_sim_scores = self._calc_similarity(doc_embeddings, topic_embeddings)

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

        return dict(zip(all_topics, result))

    def _check_cache(
        self, topic_tree: TopicTree | None = None
    ) -> tuple[list[Topic], np.ndarray]:
        if self.is_cached() and not topic_tree:
            topic_tree, embeddings = self._load_topics()

            all_topics = [
                subtopic
                for top in topic_tree.topics
                for subtopic in top.bfs()
                if subtopic not in topic_tree.topics
            ]

            return all_topics, embeddings

        if not self.is_cached() and topic_tree:
            all_topics = [
                subtopic
                for top in topic_tree.topics
                for subtopic in top.bfs()
                if subtopic not in topic_tree.topics
            ]

            topic_embeddings = self._embed_topics(all_topics)
            self._save_topics(topic_tree, topic_embeddings)
            return all_topics, topic_embeddings

        raise ValueError("no existing cache found for topics")

    def _calc_similarity(
        self, doc_embeddings: np.ndarray, topic_embeddings: np.ndarray
    ) -> np.ndarray:
        # Ensure doc_embeddings is 2D, even if a single embedding (1D) was passed
        if doc_embeddings.ndim == 1:
            doc_embeddings = np.atleast_2d(doc_embeddings)

        num_docs = doc_embeddings.shape[0]
        num_topics = topic_embeddings.shape[0]
        self._logger.info(
            "Calculating similarity for %s documents, with %s topics",
            num_docs,
            num_topics,
        )

        similarity_matrix = self._embedder.similarity(doc_embeddings, topic_embeddings)
        # similarity_matrix shape (n_doc, n_topic)

        row_min = similarity_matrix.min(axis=1).reshape(-1, 1)
        row_max = similarity_matrix.max(axis=1).reshape(-1, 1)
        normalized_similarity = (similarity_matrix - row_min) / (row_max - row_min)

        return normalized_similarity
