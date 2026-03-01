from typing import Literal

import networkx as nx
import numpy as np
import openai
from pydantic import validate_call

from wrench.grouper import BaseGrouper
from wrench.grouper.kinetic.embedder import BaseEmbedder
from wrench.grouper.kinetic.models import Cluster, Topic
from wrench.log import logger
from wrench.models import Device, Group
from wrench.utils.config import LLMConfig

from ._classifier import Classifier
from .cooccurence import build_cooccurence_network
from .defaults import DEFAULT_EMBEDDER_MODEL
from .embedder import OllamaEmbedder, SentenceTransformerEmbedder
from .keyword_extractor import KeyBERTAdapter
from .llm_topic_generator import LLMTopicGenerator
from .tracer import KineticTracer


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
        resolution (int): Size of the clusters created
    """

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        llm_config: LLMConfig,
        embedder: str | BaseEmbedder | None = None,
        lang: Literal["de", "en"] = "de",
        resolution: int = 1,
        cache_doc_embeddings: bool = False,
        enable_trace: bool = False,
        save_results: str | None = None,
    ):
        """
        Initialize the KINETIC Grouper.

        Arguments:
            llm_config (LLMConfig): The LLM configuration including host, model
                and api_key. By default this is set to use an "ollama" as the API key.
                To use OpenAI's models, generate an API key on the OpenAI Platform.
            embedder (str | BaseEmbedder | None): The embeddings model. Can be:
                - None: Uses llm_config.embedding_model for remote Ollama embeddings,
                  or falls back to local "intfloat/multilingual-e5-large-instruct".
                - str: Model name compatible with SentenceTransformers library.
                - BaseEmbedder: Custom embedder instance.
            lang (["en", "de"]): The language of the source data. Default is "de" for
                german.
            resolution (int): The resolution of the clusters, larger than 1 for smaller
                clusters, smaller than 1 for bigger clusters.
            cache_doc_embeddings (bool): Save doc_embeddings.
            enable_trace (bool): Capture a full pipeline trace and save it to
                ``.kineticache/trace.json``. Defaults to False.
            save_results (str | None): Path to save grouping results as JSON
                (topic name -> device IDs). If None, no results are saved.
        """
        if embedder is None:
            if llm_config.embedding_model:
                embedder = OllamaEmbedder(
                    base_url=llm_config.base_url,
                    model=llm_config.embedding_model,
                    api_key=llm_config.api_key,
                )
            else:
                embedder = SentenceTransformerEmbedder(DEFAULT_EMBEDDER_MODEL)
        elif isinstance(embedder, str):
            embedder = SentenceTransformerEmbedder(embedder)

        self.keyword_extractor = KeyBERTAdapter(embedder, lang=lang)

        self.classifier = Classifier(embedder)

        self.generator = LLMTopicGenerator(
            llm_client=openai.OpenAI(
                base_url=llm_config.base_url, api_key=llm_config.api_key
            ),
            model=llm_config.model,
        )

        self.resolution = resolution
        self.cache_doc_embeddings = cache_doc_embeddings
        self.enable_trace = enable_trace
        self.save_results = save_results

        self.logger = logger.getChild(self.__class__.__name__)

    def build_clusters(
        self, docs: list[str]
    ) -> tuple[list[Cluster], list[list[str]], nx.Graph, dict[str, int]]:
        self.logger.info("Extracting keywords from %s docs", len(docs))
        keywords = self.keyword_extractor.extract_keywords(docs)

        self.logger.info("Building cooccurence network")
        clusters, graph, partition = build_cooccurence_network(
            keywords, resolution=self.resolution
        )
        return clusters, keywords, graph, partition

    def generate_topics(self, clusters: list[Cluster]) -> dict[Topic, list[Device]]:
        topic_dict = self.generator.generate_seed_topics(clusters)

        return topic_dict

    def group_devices(self, devices: list[Device]) -> list[Group]:
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

        tracer = KineticTracer() if self.enable_trace else None

        doc_keywords: list[list[str]] | None = None

        if self.classifier.is_cached():
            clusters = self.classifier._load_clusters()
        else:
            clusters, doc_keywords, graph, partition = self.build_clusters(docs)
            if tracer:
                tracer.trace_documents(docs, doc_keywords)
                tracer.trace_network(graph, partition)

        if tracer:
            tracer.trace_clusters(clusters)

        doc_ids = self.classifier.classify(docs, clusters)

        if tracer:
            tracer.trace_classification(doc_ids)

        for c, ids in zip(clusters, doc_ids):
            c._devices = [devices[i] for i in ids]

        topic_dict = self.generate_topics(clusters)

        if tracer:
            tracer.trace_topics(list(topic_dict.keys()))
            tracer.set_metadata(resolution=self.resolution)
            trace_path = self.classifier.cache_dir / "trace.json"
            tracer.save(str(trace_path))
            self.logger.info("Saved pipeline trace to %s", trace_path)

        groups = []
        for topic_obj, topic_devices in topic_dict.items():
            self.logger.debug(
                "Topic %s contains devices: %s",
                topic_obj.name,
                [dev.id for dev in topic_devices],
            )
            if len(topic_devices) == 0:
                continue

            groups.append(
                Group(
                    name=topic_obj.name,
                    devices=topic_devices,
                    parent_classes=set(topic_obj.parent_topics),
                )
            )

        if self.cache_doc_embeddings:
            self._save_doc_embeddings()

        if self.save_results:
            self._save_grouping_results(groups)

        return groups

    def _save_grouping_results(self, groups: list[Group]):
        """Save topic -> device ID mapping as JSON."""
        import json
        from pathlib import Path

        output = {group.name: [str(d.id) for d in group.devices] for group in groups}
        path = Path(self.save_results)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(output, f, indent=2)
        self.logger.info("Saved grouping results to %s", path)

    def _save_doc_embeddings(self):
        """Save document embeddings from the classifier to .kineticache/."""
        embeddings = self.classifier.doc_embeddings
        if embeddings is None:
            self.logger.warning("No doc embeddings to cache")
            return

        path = self.classifier.cache_dir / "doc_embeddings.npz"
        np.savez_compressed(path, embeddings=embeddings)
        self.logger.info("Saved doc embeddings to %s", path)
