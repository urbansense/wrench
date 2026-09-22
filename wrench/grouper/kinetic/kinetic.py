import json
from pathlib import Path
from typing import Any, Literal

import openai
from pydantic import validate_call

from wrench.grouper import BaseGrouper
from wrench.grouper.kinetic.embedder import BaseEmbedder
from wrench.grouper.kinetic.models import Cluster, Topic
from wrench.log import logger
from wrench.models import Device, Group
from wrench.utils.config import LLMConfig

from ._classifier import BaseClassifier, EmbeddingClassifier
from .cooccurence import build_cooccurence_network
from .embedder import SentenceTransformerEmbedder
from .keyword_extractor import KeyBERTAdapter
from .llm_topic_generator import LLMTopicGenerator

_CACHE_DIR = Path(".kineticache")
_CLUSTERS_CACHE = _CACHE_DIR / "clusters.json"


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
        classifier (BaseClassifier): Classifies input documents into different clusters,
            created from the extracted keywords.
        generator (LLMTopicGenerator): Generates coherent topic groups based on created
            clusters.
        resolution (int): Size of the clusters created
    """

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        llm_config: LLMConfig,
        embedder: str | BaseEmbedder = "intfloat/multilingual-e5-large-instruct",
        classifier: BaseClassifier | None = None,
        lang: Literal["de", "en"] = "de",
        resolution: int = 1,
    ):
        """
        Initialize the KINETIC Grouper.

        Arguments:
            llm_config (LLMConfig): The LLM configuration including host, model
                and api_key.
            embedder (str | BaseEmbedder): The embeddings model used for keyword
                extraction (KeyBERT) and, when no custom classifier is provided,
                for document classification too. Accepts a SentenceTransformers
                model name string or a BaseEmbedder instance.
            classifier (BaseClassifier | None): Classifier to assign devices to
                clusters. Defaults to EmbeddingClassifier(embedder). Supply a
                custom implementation (e.g. JevClassifier) to replace the
                embedding-based approach entirely.
            lang (["en", "de"]): The language of the source data. Default is "de".
            resolution (int): The resolution of the clusters, larger than 1 for
                smaller clusters, smaller than 1 for bigger clusters.
        """
        if isinstance(embedder, str):
            embedder = SentenceTransformerEmbedder(embedder)

        self.keyword_extractor = KeyBERTAdapter(embedder, lang=lang)

        self.classifier = (
            classifier if classifier is not None else EmbeddingClassifier(embedder)
        )

        self.generator = LLMTopicGenerator(
            llm_client=openai.OpenAI(
                base_url=llm_config.base_url, api_key=llm_config.api_key
            ),
            model=llm_config.model,
        )

        self.resolution = resolution

        self.logger = logger.getChild(self.__class__.__name__)

    def build_clusters(self, docs: list[str]):
        self.logger.info("Extracting keywords from %s docs", len(docs))
        keywords = self.keyword_extractor.extract_keywords(docs)

        self.logger.info("Building cooccurence network")
        return build_cooccurence_network(keywords, resolution=self.resolution)

    def generate_topics(self, clusters: list[Cluster]) -> dict[Topic, list[Device]]:
        topic_dict = self.generator.generate_seed_topics(clusters)

        return topic_dict

    def group_devices(self, devices: list[Device], **kwargs: Any) -> list[Group]:
        docs = [
            device.to_string(
                exclude=[
                    "id",
                    "observed_properties",
                    "locations",
                    "time_frame",
                    "properties",
                    "_raw_data",
                    "sensors",
                ]
            )
            for device in devices
        ]

        if _CLUSTERS_CACHE.exists():
            self.logger.info("Loading cached clusters")
            with open(_CLUSTERS_CACHE) as f:
                clusters = [Cluster.model_validate(c) for c in json.load(f)]
        else:
            clusters = self.build_clusters(docs)
            _CACHE_DIR.mkdir(exist_ok=True)
            with open(_CLUSTERS_CACHE, "w") as f:
                json.dump([c.model_dump(mode="json") for c in clusters], f)

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
