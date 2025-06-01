from collections import defaultdict, deque
from typing import Sequence

import openai
from pydantic import validate_call
from sentence_transformers import SentenceTransformer

from wrench.grouper import BaseGrouper
from wrench.log import logger
from wrench.models import Device, Group

from .classifier import Classifier
from .config import LLMConfig
from .keyword_extractor import KeyBERTAdapter
from .llm_topic_generator import LLMTopicHierarchyGenerator, Topic
from .text_preprocessor import build_cooccurence_network


class KINETIC(BaseGrouper):
    """
    KINETIC: Keyword-Informed, Network-Enhanced Topical Intelligence Classifier.

    Autogenerates named and described hierarchical clusters. It leverages keyword
    extraction and co-occurrence networks to seed an LLM for generating a topic
    hierarchy. Documents are then classified into this hierarchy based on the
    cosine similarity of their embeddings with topic embeddings.

    Attributes:
        embedder (SentenceTransformer): The SentenceTransformer model to be used for
            the classification into clusters.
        client (openai.OpenAI): The OpenAI client for generating hierarchical
            cluster schema.
        llm_model (str): The LLM model used in conjunction with the OpenAI client.
        topic_embeddings (dict[str, np.ndarray]): Generated embeddings for the
            topics
    """

    @validate_call
    def __init__(
        self,
        llm_config: LLMConfig,
        embeddings_model: str = "intfloat/multilingual-e5-large-instruct",
    ):
        """
        Initialize the KINETIC Grouper.

        Arguments:
            llm_config (LLMConfig): The LLM configuration including host, model
                and api_key. By default this is set to use an "ollama" as the API key.
                To use OpenAI's models, generate an API key on the OpenAI Platform.
            embeddings_model (str): The embeddings model compatible with the
                `SentenceTransformers` library. Defaults to
                `intfloat/multilingual-e5-large-instruct`, use `all-MiniLM-L12-v2` for
                english data.
        """
        embedder = SentenceTransformer(embeddings_model)

        self.llm_model = llm_config.model
        self.client = openai.OpenAI(
            base_url=llm_config.base_url, api_key=llm_config.api_key
        )
        self.classifier = Classifier(embedder)
        self.keyword_extractor = KeyBERTAdapter(embedder, lang="de")
        self.logger = logger.getChild(self.__class__.__name__)

    def get_topics(self, docs: list[str]):
        keywords = self.keyword_extractor.extract_keywords(docs)

        clusters = build_cooccurence_network(keywords)

        generator = LLMTopicHierarchyGenerator(
            llm_client=self.client,
            model=self.llm_model,
        )

        root_topics = generator.generate_seed_topics(clusters)

        return root_topics

    def _build_ancestor_map(self, root_topics_list: list[Topic]) -> dict[str, str]:
        """Builds a map from any topic name to its ultimate root ancestor's name."""
        child_to_root_map: dict[str, str] = {}
        for root_topic in root_topics_list:
            queue = deque(root_topic.subtopics)
            visited_descendants = {root_topic}  # Avoid reprocessing, include root

            while queue:
                current_descendant = queue.popleft()
                if current_descendant in visited_descendants:
                    continue
                visited_descendants.add(current_descendant)

                child_to_root_map[current_descendant.name] = root_topic.name

                for sub_desc in current_descendant.subtopics:
                    if sub_desc not in visited_descendants:
                        queue.append(sub_desc)
        return child_to_root_map

    def group_items(self, devices: Sequence[Device]) -> list[Group]:
        docs = [f"{device.name} {device.description}".strip() for device in devices]

        root_topics = self.get_topics(docs)

        # Build the map from child topic names to their ultimate root ancestor names
        child_to_root_ancestor_map = self._build_ancestor_map(root_topics.topics)

        topic_lists = self.classifier.classify(docs, root_topics.topics)

        topic_dict: dict[Topic, list] = defaultdict(list)

        for i, (_, topics) in enumerate(zip(docs, topic_lists)):
            if topics:
                for t in topics:
                    topic_dict[t].append(devices[i])

        for topic, device_list in topic_dict.items():
            self.logger.debug(
                "Topic %s contains devices: %s",
                topic.name,
                [device.id for device in device_list],
            )

        groups = []
        for topic_obj, device_list in topic_dict.items():
            if not topic_obj.subtopics:  # Create groups only for leaf topics
                top_level_ancestor_name = child_to_root_ancestor_map.get(topic_obj.name)
                parent_classes_set = (
                    {top_level_ancestor_name} if top_level_ancestor_name else set()
                )

                groups.append(
                    Group(
                        name=topic_obj.name,
                        devices=device_list,
                        parent_classes=parent_classes_set,
                    )
                )

        return groups

    def process_operations(
        self,
        existing_groups: Sequence[Group],
        devices_to_add: Sequence[Device],
        devices_to_update: Sequence[Device],
        devices_to_delete: Sequence[Device],
    ):
        pass
