import openai
from pydantic import validate_call

from wrench.grouper import BaseGrouper
from wrench.grouper.cluster.embedder import BaseEmbedder, SentenceTransformerEmbedder
from wrench.log import logger
from wrench.models import Device, Group

from ._classifier import Classifier
from .config import LLMConfig
from .cooccurence import build_cooccurence_network
from .keyword_extractor import KeyBERTAdapter
from .llm_topic_generator import LLMTopicGenerator
from .models import Cluster, Topic


class KINETIC(BaseGrouper):
    """
    KINETIC: Keyword-Informed, Network-Enhanced Topical Intelligence Classifier.

    Autogenerates named and described hierarchical clusters. It leverages keyword
    extraction and co-occurrence networks to seed an LLM for generating a topic
    hierarchy. Documents are then classified into this hierarchy based on the
    cosine similarity of their embeddings with topic embeddings.

    Attributes:
        keyword_extractor (KeyBERTAdapter): Uses KeyBERT to extract keywords from a
            list of document bodies.
        classifier (Classifier): Classifies input documents into different clusters,
            created from the extracted keywords.
        generator (LLMTopicGenerator): Generates coherent topic groups based on created
            clusters.
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
        self.classifier = Classifier(embedder, threshold)

        self.generator = LLMTopicGenerator(
            llm_client=openai.OpenAI(
                base_url=llm_config.base_url, api_key=llm_config.api_key
            ),
            model=llm_config.model,
        )

        self.logger = logger.getChild(self.__class__.__name__)

    def build_clusters(self, docs: list[str]):
        keywords = self.keyword_extractor.extract_keywords(docs)

        clusters = build_cooccurence_network(keywords)

        return [
            Cluster(cluster_id=id, keywords=keywords)
            for id, keywords in clusters.items()
        ]

    def generate_topics(self, clusters: list[Cluster]) -> dict[Topic, list[Device]]:
        topic_dict = self.generator.generate_seed_topics(clusters)

        return topic_dict

    def group_items(self, devices: list[Device]) -> list[Group]:
        docs = [f"{device.name} {device.description}".strip() for device in devices]

        if self.classifier.is_cached():
            clusters = self.classifier._load_clusters()
        else:
            clusters = self.build_clusters(docs)

        doc_ids = self.classifier.classify(docs, clusters)

        for c, ids in zip(clusters, doc_ids):
            c._devices = [devices[i] for i in ids]

        topic_dict = self.generate_topics(clusters)

        groups = []
        for topic_obj, devices in topic_dict.items():
            self.logger.debug(
                "Topic %s contains devices: %s",
                topic_obj.name,
                [dev.id for dev in devices],
            )
            if len(devices) == 0:
                continue

            groups.append(
                Group(
                    name=topic_obj.name,
                    devices=devices,
                    parent_classes=set(topic_obj.parent_topics),
                )
            )

        return groups
