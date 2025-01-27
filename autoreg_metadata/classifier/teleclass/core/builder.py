import networkx as nx
from ollama import Client
from pydantic import BaseModel

from autoreg_metadata.classifier.teleclass.core.embeddings import EmbeddingService
from autoreg_metadata.classifier.teleclass.core.taxonomy_manager import TaxonomyManager
from autoreg_metadata.classifier.teleclass.core.teleclass import TELEClass
from autoreg_metadata.classifier.teleclass.enrichment.corpus import CorpusEnricher
from autoreg_metadata.classifier.teleclass.enrichment.llm import LLMEnricher


class TELEClassConfig(BaseModel):
    """Default configuration for TELEClass"""

    EMBEDDINGS_MODEL: str = "all-mpnet-base-v2"
    LLM_HOST: str = "http://localhost:11434"
    DEFAULT_TAXONOMY: set[tuple[str, str]] = set(
        {
            # ("domain", "mobility"),
            # ("domain", "health"),
            # ("domain", "information technology"),
            # ("domain", "energy"),
            # ("domain", "environment"),
            # ("domain", "trade"),
            # ("domain", "construction"),
            # ("domain", "culture"),
            # ("domain", "administration"),
            # ("domain", "urban planning"),
            # ("domain", "education"),
            ("mobility", "public transport"),
            ("mobility", "shared mobility"),
            ("mobility", "traffic management"),
            ("mobility", "vehicle infrastructure"),
            ("environment", "weather monitoring"),
            ("environment", "air quality monitoring"),
            ("environment", "water quality monitoring"),
            ("environment", "water level monitoring"),
            ("environment", "soil moisture monitoring"),
        }
    )


class TELEClassBuilder:
    """Builder class for easy TELEClass initialization."""

    def __init__(self):
        self._config = TELEClassConfig()
        self._custom_taxonomy: set[tuple[str, str]] | None = None
        self._custom_embedder: EmbeddingService | None = None
        self._custom_llm_client: Client | None = None
        self._use_cache: bool = True

    def with_custom_taxonomy(self, edges: set[tuple[str, str]]) -> "TELEClassBuilder":
        """set a custom taxonomy"""
        self._custom_taxonomy = edges
        return self

    def with_custom_embedder(self, embedder: EmbeddingService) -> "TELEClassBuilder":
        """set a custom embedder"""
        self._custom_embedder = embedder
        return self

    def with_custom_llm(self, host: str) -> "TELEClassBuilder":
        """set a custom LLM client"""
        self._custom_llm_client = Client(host=host)
        return self

    def build(self) -> TELEClass:
        """Build the TELEClass instance"""
        # Initialize taxonomy
        graph = nx.DiGraph()
        taxonomy_edges = self._custom_taxonomy or self._config.DEFAULT_TAXONOMY
        graph.add_edges_from(taxonomy_edges)
        taxonomy_manager = TaxonomyManager(graph)

        # Initialize embeddings service
        embedder = self._custom_embedder or EmbeddingService(
            self._config.EMBEDDINGS_MODEL
        )

        # Initialize LLM client
        llm_client = self._custom_llm_client or Client(host=self._config.LLM_HOST)

        # Initialize enrichers
        llm_enricher = LLMEnricher(model=llm_client, taxonomy_manager=taxonomy_manager)
        corpus_enricher = CorpusEnricher(
            model_name=self._config.EMBEDDINGS_MODEL, phrase_extractor="yake"
        )

        # Create and return TELEClass instance
        return TELEClass(
            taxonomy_manager=taxonomy_manager,
            llm_enricher=llm_enricher,
            corpus_enricher=corpus_enricher,
            embedding_service=embedder,
            use_cache=self._use_cache,
        )
