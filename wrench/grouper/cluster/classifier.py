from collections import deque

import numpy as np
from sentence_transformers import SentenceTransformer

from wrench.log import logger as wrench_logger
from wrench.utils.prompt_manager import PromptManager

from .llm_topic_generator import Topic

_TOPIC_PROMPT = PromptManager.get_prompt("embed_topics.txt")
_DOC_PROMPT = PromptManager.get_prompt("embed_documents.txt")


def _min_max_norm(nums: list[float]) -> list[float]:
    minima = min(nums)
    delta = max(nums) - minima

    if delta == 0:
        return [(num - minima) for num in nums]

    return [(num - minima) / delta for num in nums]


class Classifier:
    def __init__(self, st_model: SentenceTransformer):
        self._st_model = st_model
        self._logger = wrench_logger.getChild(self.__class__.__name__)
        self._topic_embeddings = {}

    def _embed_topics(self, topics: list[Topic]):
        for topic in topics:
            self._topic_embeddings[topic.name] = self._st_model.encode(
                f"{topic.name}; {','.join(topic.keywords)}",
                prompt=_TOPIC_PROMPT.format(topic_name=topic.name),
                convert_to_numpy=True,
            )
            # Recursively process subtopics if they exist
            if topic.subtopics:
                self._embed_topics(topic.subtopics)

    def classify(self, docs: list[str], topics: list[Topic]) -> list[list[Topic]]:
        if not topics:
            return []

        self._embed_topics(topics)

        doc_embeddings = self._st_model.encode(
            docs, prompt=_DOC_PROMPT, convert_to_numpy=True
        )

        all_sim_scores = self._calc_similarity(doc_embeddings, topics)

        all_selected_topics: list[list[Topic]] = []

        for sim_scores_for_doc in all_sim_scores:
            if not sim_scores_for_doc:
                self._logger.debug("No similar topics found for a document")
                all_selected_topics.append([])
                continue

            if all(v == 0 for v in sim_scores_for_doc.values()):
                self._logger.debug(
                    "No similar topics found for a document as all scores are 0"
                )
                all_selected_topics.append([])
                continue

            normed_scores = _min_max_norm(list(sim_scores_for_doc.values()))
            normed_sim_scores = dict(zip(sim_scores_for_doc.keys(), normed_scores))

            selected_topics_for_doc = [
                topic
                for topic, normalized_score in normed_sim_scores.items()
                if normalized_score > 0.9  # TODO: Make this threshold configurable
            ]

            # Log an error if all selected topics are from root_topics
            if selected_topics_for_doc and all(
                top in topics for top in selected_topics_for_doc
            ):
                self._logger.error(
                    (
                        "document does not have any assigned topics from sub-topics",
                        "consider re-running generate topics",
                    ),
                )

            all_selected_topics.append(selected_topics_for_doc)

        return all_selected_topics

    def _calc_similarity(
        self, doc_embeddings: np.ndarray, topics: list[Topic]
    ) -> list[dict[Topic, float]]:
        # Ensure doc_embeddings is 2D, even if a single embedding (1D) was passed
        if doc_embeddings.ndim == 1:
            doc_embeddings = np.atleast_2d(doc_embeddings)

        num_docs = doc_embeddings.shape[0]

        # Initialize a list of dictionaries, one for each document
        all_sim_scores: list[dict[Topic, float]] = [{} for _ in range(num_docs)]

        queue = deque(topics)
        visited_for_calc: set[Topic] = set()

        while queue:
            topic = queue.popleft()
            if topic in visited_for_calc:
                continue
            visited_for_calc.add(topic)

            topic_embedding = self._topic_embeddings.get(topic.name)
            if topic_embedding is None:
                self._logger.warning(f"No embedding for topic {topic.name}")
                continue

            # Reshape topic_embedding to 2D: [1, embedding_dim]
            topic_embedding_2d = np.atleast_2d(topic_embedding)

            # doc_embeddings is [num_docs, D]
            # similarity_matrix will be [num_docs, 1]
            similarity_matrix = self._st_model.similarity(
                doc_embeddings, topic_embedding_2d
            )

            # raw_similarities_for_topic is a 1D array of shape [num_docs]
            raw_similarities_for_topic = similarity_matrix[:, 0]

            for i in range(num_docs):
                current_doc_raw_similarity = raw_similarities_for_topic[i]
                all_sim_scores[i][topic] = float(current_doc_raw_similarity)

            for subtopic in topic.subtopics:
                if subtopic not in visited_for_calc:
                    queue.append(subtopic)

        return all_sim_scores
