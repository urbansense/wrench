from collections import defaultdict
from pathlib import Path
from typing import Union

import numpy as np
from sentence_transformers import SentenceTransformer

from wrench.grouper.base import BaseGrouper
from wrench.grouper.teleclass.classifier.similarity import SimilarityClassifier
from wrench.grouper.teleclass.core.cache import TELEClassCache
from wrench.grouper.teleclass.core.config import TELEClassConfig
from wrench.grouper.teleclass.core.document_loader import ModelDocumentLoader
from wrench.grouper.teleclass.core.models import (
    CorpusEnrichmentResult,
    Document,
    EnrichedClass,
    LLMEnrichmentResult,
)
from wrench.grouper.teleclass.core.taxonomy_manager import TaxonomyManager
from wrench.grouper.teleclass.enrichment.corpus import CorpusEnricher
from wrench.grouper.teleclass.enrichment.llm import LLMEnricher
from wrench.log import logger
from wrench.models import Device, Group


class TELEClassGrouper(BaseGrouper):
    """Main class for taxonomy-enhanced text classification.

    This class provides functionality for classifying documents using a taxonomy-
    enhanced approach that combines LLM-based enrichment with corpus-based
    classification.

    Attributes:
        config (TELEClassConfig): Configuration settings for the classifier.
        taxonomy_manager (TaxonomyManager): Manages taxonomy relationships.
        encoder (SentenceTransformer): Model for encoding text into embeddings.
        llm_enricher (LLMEnricher): Handles LLM-based enrichment operations.
        corpus_enricher (CorpusEnricher): Handles corpus-based enrichment operations.
        enriched_classes (list[EnrichedClass]): Classes with their enriched terms.
        cache (TELEClassCache, optional): Caches intermediate results if enabled.
        logger (Logger): Logger instance for this class.
    """

    def __init__(self, config: TELEClassConfig | str | Path):
        """Initializes the TELEClass classifier.

        Args:
            config: Configuration for the classifier. Can be:
                - TELEClassConfig: Direct config object
                - str or Path: Path to YAML config file

        Raises:
            FileNotFoundError: If config file path doesn't exist.
            ValidationError: If config file contains invalid settings.
        """
        # Load config if path is provided
        if isinstance(config, (str, Path)):
            config = TELEClassConfig.from_yaml(config)

        self.config = config
        # Initialize components
        self.taxonomy_manager = TaxonomyManager.from_config(config.taxonomy)
        self.encoder = SentenceTransformer(config.embedding.model_name)
        # Initialize enrichers
        self.llm_enricher = LLMEnricher(
            config=config.llm, taxonomy_manager=self.taxonomy_manager
        )
        self.corpus_enricher = CorpusEnricher(
            config=config.corpus, encoder_model=config.embedding.model_name
        )

        # initialize empty set of terms for all classes, embeddings are not yet set here
        self.enriched_classes = [
            EnrichedClass(class_name=name, class_description=description, terms=set())
            for name, description in self.taxonomy_manager.get_cls_with_desc().items()
        ]
        # Initialize cache
        self.cache = TELEClassCache(config.cache.directory)

        self.logger = logger.getChild(self.__class__.__name__)

    def _load_devices(self, source: Union[str, Path, list[Device]]) -> list[Document]:
        loader = ModelDocumentLoader(source)

        return loader.load(self.encoder)

    def run(self, documents: list[Document], sample_size: int = 20) -> None:
        """
        Executes the training process on a given list of documents.

        This method performs the following steps:
        1. Performs LLM-enhanced core class annotation on the documents.
        2. Performs corpus-based enrichment on the documents.

        Args:
            documents (list[DocumentMeta]): The list of documents to use for training.
            sample_size (int, optional): The maximum number of documents to use.
                                         Defaults to 20.

        Raises:
            Exception: If any error occurs during the training process,
                       it is logged and re-raised.
        """
        self.logger.info("Starting training process")
        documents = documents[: min(len(documents), sample_size)]

        self.logger.info("Training with %d documents", len(documents))

        try:
            # Stage 1: LLM-Enhanced Core Class Annotation
            self.enriched_classes, documents = self._perform_llm_enrichment(
                collection=documents
            ).result

            self.logger.info("Finished assignments with LLM enrichment step")

            # Stage 2: Corpus-Based Enrichment

            self.enriched_classes = self._perform_corpus_enrichment(documents).result

            self.logger.info("Finished corpus-based enrichment step.")

            self._save_class_embeddings()

            self.cache.save_class_embeddings(self.enriched_classes)

        except Exception as e:
            self.logger.error("Training failed: %s", e)
            raise

    def _perform_llm_enrichment(
        self, collection: list[Document]
    ) -> LLMEnrichmentResult:
        """Perform LLM-based taxonomy enrichment."""
        self.logger.info("Performing LLM enrichment")
        if not self.config.cache.enabled:
            return self.llm_enricher.enrich(
                enriched_classes=self.enriched_classes, collection=collection
            )

        # try loading from cache
        llm_class_terms = self.cache.load_class_terms()
        assignments = self.cache.load_assignments()

        if llm_class_terms and assignments:
            return LLMEnrichmentResult(
                ClassEnrichment=llm_class_terms, DocumentCoreClasses=assignments
            )
        # if class terms exist but no assignments, use them to generate assignments
        if llm_class_terms:
            assignments = self.llm_enricher.assign_classes_to_docs(
                collection=collection, enriched_classes=llm_class_terms
            )
            self.cache.save_assignments(assignments)
            return LLMEnrichmentResult(
                ClassEnrichment=llm_class_terms, DocumentCoreClasses=assignments
            )

        # nothing in cache, run full process
        # when you move cache responsibility to LLMEnricher, this will be simpler
        llm_class_terms = self.llm_enricher.enrich_classes_with_terms(
            enriched_classes=self.enriched_classes
        )
        if llm_class_terms is not None:
            self.cache.save_class_terms(llm_class_terms)

        assignments = self.llm_enricher.assign_classes_to_docs(
            collection=collection, enriched_classes=llm_class_terms
        )
        self.cache.save_assignments(assignments)

        return LLMEnrichmentResult(
            ClassEnrichment=llm_class_terms, DocumentCoreClasses=assignments
        )

    def _perform_corpus_enrichment(
        self,
        collection: list[Document],
    ) -> CorpusEnrichmentResult:
        """Perform corpus-based enrichment."""
        self.logger.info("Performing corpus-based enrichment")
        corpus_enrichment_result = self.corpus_enricher.enrich(
            enriched_classes=self.enriched_classes, collection=collection
        )

        # Cache results if enabled
        if self.config.cache.enabled:
            try:
                self.cache.save_class_terms(corpus_enrichment_result.ClassEnrichment)
                self.logger.debug("Successfully cached corpus enrichment results")
            except Exception as e:
                self.logger.warning("Failed to cache enrichment results: %s", str(e))

        return corpus_enrichment_result

    def _save_class_embeddings(self):
        """Averages class term embeddings to create class representation."""
        for ec in self.enriched_classes:
            if ec.embeddings is not None:
                # Use pre-computed embeddings
                ec.embeddings = np.mean(ec.embeddings, axis=0)

        self.cache.save_class_embeddings(self.enriched_classes)

    def predict(self, text: str) -> set[str]:
        """
        Predict classes for a given text.

        Args:
            text (str): The input text to classify.

        Returns:
            set[str]: A set of predicted classes for the input text.
        """
        enriched_classes = self.cache.load_class_embeddings()

        # initialize classifier manager
        self.classifier_manager = SimilarityClassifier(
            taxonomy_manager=self.taxonomy_manager,
            encoder=self.encoder,
            enriched_classes=enriched_classes,
        )

        return self.classifier_manager.predict(text)

    def group_devices(self, devices: list[Device]) -> list[Group]:
        """
        Groups a collection of documents into predefined categories.

        Args:
            devices (list[Device]]): The items to classify.

        Returns:
            list[Group]: A list of Groups containing information about documents
                         classified and group parent classes
        """
        self.logger.debug("Starting document classification")

        try:
            docs = self._load_devices(devices)
            self.logger.debug("Loaded %d items", len(docs))
            if not hasattr(self, "classifier_manager"):
                self.run(docs)

            leaf_nodes = self.taxonomy_manager.get_leaf_nodes()
            leaf_classifications: dict[str, list[Document]] = defaultdict(list)

            for d in docs:
                self.logger.debug("Processing document %s", d.id)
                classes = self.predict(text=d.content)
                self.logger.debug("Predicted classes: %s", classes)
                leaf_predictions = classes & leaf_nodes
                for leaf_class in leaf_predictions:
                    leaf_classifications[leaf_class].append(d)

            groups = []
            for leaf_class, class_docs in leaf_classifications.items():
                groups.append(
                    Group(
                        name=leaf_class,
                        devices=[
                            Device.model_validate_json(doc.content)
                            for doc in class_docs
                        ],
                        parent_classes=self.taxonomy_manager.get_ancestors(leaf_class),
                    )
                )

            return groups

        except Exception as e:
            self.logger.exception("Classification failed with error: %s", str(e))
            raise
