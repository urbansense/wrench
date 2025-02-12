from collections import defaultdict
from typing import List, Set

import numpy as np
from ollama import Client
from sentence_transformers import SentenceTransformer

from autoreg_metadata.grouper.teleclass.core.config import LLMConfig
from autoreg_metadata.grouper.teleclass.core.models import (
    DocumentMeta,
    EnrichedClass,
    LLMEnrichmentResult,
    TermScore,
)
from autoreg_metadata.grouper.teleclass.core.taxonomy_manager import TaxonomyManager
from autoreg_metadata.log import logger


class LLMEnricher:
    def __init__(self, config: LLMConfig, taxonomy_manager: TaxonomyManager):
        self.llm = Client(host=config.host)
        self.model = config.model
        self.temperature = config.temperature
        self.taxonomy_manager = taxonomy_manager
        self.prompt = (
            config.prompt
            or """
            Generate 10 specific urban sensor use case keywords for the class '{class_name}' described as '{class_description}' which is a subclass of '{parent_class}'.
            These keywords should be relevant to '{class_name}' but not to these sibling classes: {siblings}. Be specific and relevant.
            Respond with only the comma-separated terms, no explanations.
            """
        )
        self.encoder = SentenceTransformer("all-mpnet-base-v2")

        self.logger = logger.getChild(self.__class__.__name__)

    def process(
        self, enriched_classes: list[EnrichedClass], collection: List[DocumentMeta]
    ) -> LLMEnrichmentResult:
        """Process generates both terms for each classes, and runs the core class selection for documents"""
        class_with_terms = self.enrich_classes_with_terms(enriched_classes)
        document_with_core_classes = self.assign_classes_to_docs(
            collection=collection, enriched_classes=class_with_terms
        )

        return LLMEnrichmentResult(
            ClassEnrichment=class_with_terms,
            DocumentCoreClasses=document_with_core_classes,
        )

    def enrich_classes_with_terms(
        self, enriched_classes: list[EnrichedClass]
    ) -> list[EnrichedClass]:
        for ec in enriched_classes:
            # Get all nodes that are parents of the current node
            parents = list(self.taxonomy_manager.get_parents(ec.class_name))
            # Check if node is root (have no parents)
            if parents:
                for parent in parents:
                    # Get all siblings of the node
                    siblings = self.taxonomy_manager.get_siblings(ec.class_name)

                    terms = self.enrich_class(
                        class_name=ec.class_name,
                        class_description=ec.class_description,
                        parent_class=parent,
                        siblings=siblings,
                    )
                    if terms:  # Only update if we got valid terms
                        ec.terms.update(terms)
            else:
                # Root node or node without parents
                terms = self.enrich_class(
                    class_name=ec.class_name,
                    class_description=ec.class_description,
                    parent_class="",
                    siblings=set(),
                )
                if terms:
                    ec.terms.update(terms)

            # Compute embeddings for the terms
            if ec.terms:
                embeddings = self.encoder.encode(
                    [term_score.term for term_score in ec.terms]
                )
                ec.embeddings = embeddings

            self.logger.info("Enriched terms for %s: %s", ec.class_name, ec.terms)

        return enriched_classes

    def enrich_class(
        self,
        class_name: str,
        class_description: str,
        parent_class: str,
        siblings: Set[str],
    ) -> Set[TermScore]:
        """
        Enrich a class by generating class-specific terms using a language model (LLM) with parent and sibling context.

        Args:
            class_name (str): The name of the class to enrich.
            class_description (str): A description of the class.
            parent_class (str): The name of the parent class.
            siblings (Set[str]): A set of sibling class names.

        Returns:
            Set[TermScore]: A set of TermScore objects representing the generated terms.

        Raises:
            Exception: If there is an error during term generation, it logs the error and returns an empty set.
        """
        try:
            siblings_str = ", ".join(siblings) if siblings else "none"
            parent_str = parent_class if parent_class else "root"
            prompt = self.prompt.format(
                class_name=class_name,
                class_description=class_description,
                parent_class=parent_str,
                siblings=siblings_str,
            )

            self.logger.info(
                "Generating terms for class: %s, with description: %s",
                class_name,
                class_description,
            )

            response = self.llm.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": self.temperature},
            )

            if not response:
                self.logger.warning("Empty response from LLM for class: %s", class_name)
                return set()

            terms = response["message"]["content"].strip().split(",")
            self.logger.info("Generated terms for %s: %s", class_name, terms)

            return set(TermScore(term=term.strip()) for term in terms)

        except Exception as e:
            self.logger.error("Error generating terms for %s: %s", class_name, str(e))
            return set()

    def assign_classes_to_docs(
        self, collection: List[DocumentMeta], enriched_classes: list[EnrichedClass]
    ) -> List[DocumentMeta]:
        """Assign initial classes to documents"""
        self.logger.info("Assigning initial classes")

        for doc in collection:
            candidates = self._select_candidates_for_document(
                doc_embedding=doc.embeddings,
                taxonomy_manager=self.taxonomy_manager,
                enriched_classes=enriched_classes,
            )

            self.logger.info("Candidates for document %s: %s", doc.id, candidates)
            core_classes = self._select_core_classes(doc.content, candidates)
            doc.core_classes = set(core_classes)
            self.logger.info(
                "Assigned classes for document %s: %s", doc.id, core_classes
            )

        return collection

    def _select_core_classes(
        self, doc: str, candidates: dict[int, set[str]]
    ) -> List[str]:
        """
        Select core classes from a list of candidates using LLM
        """
        try:
            candidates_text = []
            for level in sorted(candidates.keys()):
                classes = sorted(candidates[level])
                candidates_text.append(f"Level {level}: {', '.join(classes)}")
            formatted_candidates = "\n".join(candidates_text)

            prompt = f"""Given this document:
"{doc}"

And these possible classes by level:
{formatted_candidates}


Select ONLY the most specific and directly relevant class that best describe the main topics of this document.
Important guidelines:
- Choose the class that is most specific to the document's content at each level
- Exclude broad/general classes unless they are directly discussed
- Only select ONE class maximum per level
- If uncertain about a class, exclude it

Return only the selected class names separated by commas, nothing else."""

            response = self.llm.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": self.temperature},
            )

            if not response:
                self.logger.warning(
                    "Empty response from LLM for core classes selection"
                )
                return []

            core_classes = response["message"]["content"].strip().split(",")
            self.logger.info("Selected core classes: %s", core_classes)

            return [cls.strip() for cls in core_classes]

        except Exception as e:
            self.logger.error("Error selecting core classes: %s", str(e))
            return []

    def _select_candidates_for_document(
        self,
        doc_embedding: np.ndarray,
        taxonomy_manager: TaxonomyManager,
        enriched_classes: list[EnrichedClass],
    ) -> dict[int, set[str]]:
        """Select candidate classes for a document using level-wise traversal"""
        candidates = defaultdict(set)
        current_level = set(taxonomy_manager.root_nodes)

        self.logger.info("Taxonomy max depth is %d", taxonomy_manager.max_depth + 1)
        for level in range(taxonomy_manager.max_depth + 1):
            if not current_level:
                break

            # Calculate similarities for current level
            similarities = []
            for ec in enriched_classes:
                if ec.class_name in current_level:
                    similarities.append(
                        (ec.class_name, self._compute_similarity(doc_embedding, ec))
                    )

            # Select top candidates
            similarities.sort(key=lambda x: x[1], reverse=True)
            selected = {node for node, _ in similarities[: level + 2]}
            candidates[level].update(selected)

            # Prepare next level
            current_level = {
                child
                for node in selected
                for child in taxonomy_manager.taxonomy.successors(node)
            }
            self.logger.info("Candidates at level %d: %s", level, selected)

        return candidates

    def _compute_similarity(
        self, embedding: np.ndarray, enriched_class: EnrichedClass
    ) -> float:
        """Compute similarity between a document and an enriched class"""
        if enriched_class is None:
            self.logger.error("enriched_class is None")
            return 0.0

        if not hasattr(enriched_class, "embeddings"):
            self.logger.error(
                "Class %s has no embeddings attribute", enriched_class.terms
            )
            return 0.0

        if enriched_class.embeddings is None:
            self.logger.error("Class %s has None embeddings", enriched_class.terms)
            return 0.0

        if embedding is None:
            self.logger.error("Document embedding is None")
            return 0.0

        return np.max(
            [
                self.encoder.similarity(embedding, term_embedding)
                for term_embedding in enriched_class.embeddings
            ]
        )
