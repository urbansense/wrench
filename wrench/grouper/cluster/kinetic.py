from collections import deque

import openai
from pydantic import validate_call

from wrench.grouper import BaseGrouper
from wrench.grouper.cluster.embedder import BaseEmbedder, SentenceTransformerEmbedder
from wrench.log import logger
from wrench.models import Device, Group

from ._classifier import Classifier
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
    """

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        llm_config: LLMConfig,
        embedder: str | BaseEmbedder = "intfloat/multilingual-e5-large-instruct",
        threshold=0.9,
    ):
        """
        Initialize the KINETIC Grouper.

        Arguments:
            llm_config (LLMConfig): The LLM configuration including host, model
                and api_key. By default this is set to use an "ollama" as the API key.
                To use OpenAI's models, generate an API key on the OpenAI Platform.
            embedder (str): The embeddings model compatible with the
                `SentenceTransformers` library. Defaults to
                `intfloat/multilingual-e5-large-instruct`, use `all-MiniLM-L12-v2` for
                english data.
            threshold (float): The threshold for the similarity comparison. Defaults to
                0.9. This parameter is the first one to change in order to get better
                classifications for your data.
        """
        if isinstance(embedder, str):
            embedder = SentenceTransformerEmbedder(embedder)

        self.keyword_extractor = KeyBERTAdapter(embedder, lang="de")
        self.llm_model = llm_config.model
        self.client = openai.OpenAI(
            base_url=llm_config.base_url, api_key=llm_config.api_key
        )
        self.classifier = Classifier(embedder, threshold)
        self.logger = logger.getChild(self.__class__.__name__)

    def get_topics(self, docs: list[str]):
        keywords = self.keyword_extractor.extract_keywords(docs)

        import json

        with open("keywords.json", "w") as f:
            json.dump(keywords, f)

        clusters = build_cooccurence_network(keywords)

        generator = LLMTopicHierarchyGenerator(
            llm_client=self.client,
            model=self.llm_model,
        )

        topic_tree = generator.generate_seed_topics(clusters)

        return topic_tree

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

    def group_items(self, devices: list[Device]) -> list[Group]:
        docs = [f"{device.name} {device.description}".strip() for device in devices]

        if self.classifier.is_cached():
            topic_tree = self.classifier._load_topics()
        else:
            topic_tree = self.get_topics(docs)

        # Build the map from child topic names to their ultimate root ancestor names
        ancestor_map = self._build_ancestor_map(topic_tree.topics)

        topic_dict = self.classifier.classify(docs, topic_tree)

        groups = []
        for topic_obj, ids in topic_dict.items():
            self.logger.debug(
                "Topic %s contains devices: %s",
                topic_obj.name,
                [devices[i].id for i in ids],
            )
            if not topic_obj.is_leaf() or ids.shape == 0:
                continue

            top_level_ancestor_name = ancestor_map.get(topic_obj.name)
            parent_classes_set = (
                {top_level_ancestor_name} if top_level_ancestor_name else set()
            )

            groups.append(
                Group(
                    name=topic_obj.name,
                    devices=[devices[i] for i in ids],
                    parent_classes=parent_classes_set,
                )
            )

        return groups
