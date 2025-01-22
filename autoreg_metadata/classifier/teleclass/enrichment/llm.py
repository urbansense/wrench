import logging
from typing import Dict, List, Set

import numpy as np
from networkx import DiGraph
from ollama import Client
from sentence_transformers import SentenceTransformer

from autoreg_metadata.classifier.teleclass.core.models.enrichment_models import (
    EnrichedClass,
    LLMEnrichmentResult,
    TermScore,
)
from autoreg_metadata.classifier.teleclass.core.models.models import DocumentMeta
from autoreg_metadata.classifier.teleclass.core.taxonomy_manager import TaxonomyManager

logger = logging.getLogger(__name__)


class LLMEnricher:
    def __init__(self, model: Client, taxonomy_manager: TaxonomyManager):
        self.llm = model
        self.taxonomy_manager = taxonomy_manager
        self.prompt = """
            Generate 10 specific urban sensor use case keywords for the class '{class_name}' which is a subclass of '{parent_class}'.
            These keywords should be relevant to '{class_name}' but not to these sibling classes: {siblings}. Be specific and relevant.
            Respond with only the comma-separated terms, no explanations.
            """
        self.encoder = SentenceTransformer("all-mpnet-base-v2")
        # Initialize empty sets for all nodes in the taxonomy
        self.class_terms: Dict[str, EnrichedClass] = {
            node: EnrichedClass(class_name=node, terms=set())
            for node in self.taxonomy_manager.get_all_classes()
        }

    def process(self, collection: List[DocumentMeta]) -> LLMEnrichmentResult:
        """Process generates both terms for each classes, and runs the core class selection for documents"""
        class_with_terms = self.enrich_classes_with_terms()
        document_with_core_classes = self.assign_classes_to_docs(
            collection=collection, enriched_classes=class_with_terms
        )

        return LLMEnrichmentResult(
            ClassEnrichment=class_with_terms,
            DocumentCoreClasses=document_with_core_classes,
        )

    def enrich_classes_with_terms(self) -> Dict[str, EnrichedClass]:
        for node_name, class_term in self.class_terms.items():
            # Get all nodes that are parents of the current node
            parents = list(self.taxonomy_manager.get_parents(node_name))
            # Check if node is root (have no parents)
            if parents:
                for parent in parents:
                    # Get all siblings of the node
                    siblings = self.taxonomy_manager.get_siblings(node_name)

                    terms = self.enrich_class(node_name, parent, siblings)
                    if terms:  # Only update if we got valid terms
                        class_term.terms.update(terms)
            else:
                # Root node or node without parents
                terms = self.enrich_class(node_name, "", set())
                if terms:
                    class_term.terms.update(terms)

            # Compute embeddings for the terms
            if class_term.terms:
                embeddings = self.encoder.encode(
                    [term_score.term for term_score in class_term.terms]
                )
                class_term.embeddings = embeddings

            logger.info("Enriched terms for %s: %s",
                        node_name, class_term.terms)

        return self.class_terms

    def enrich_class(
        self, class_name: str, parent_class: str, siblings: Set[str]
    ) -> Set[TermScore]:
        """
        Use LLM to generate class-specific terms with parent and sibling as context
        """
        try:
            siblings_str = ", ".join(siblings) if siblings else "none"
            parent_str = parent_class if parent_class else "root"
            prompt = self.prompt.format(
                class_name=class_name, parent_class=parent_str, siblings=siblings_str
            )

            logger.info("Generating terms for class: %s", class_name)

            response = self.llm.chat(
                model="llama3.2:3b-instruct-fp16",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
            )

            if not response:
                logger.warning(
                    "Empty response from LLM for class: %s", class_name)
                return set()

            terms = response["message"]["content"].strip().split(",")
            logger.info("Generated terms for %s: %s", class_name, terms)

            return set(TermScore(term=term.strip()) for term in terms)

        except Exception as e:
            logger.error("Error generating terms for %s: %s",
                         class_name, str(e))
            return set()

    def assign_classes_to_docs(
        self, collection: List[DocumentMeta], enriched_classes: Dict[str, EnrichedClass]
    ) -> List[DocumentMeta]:
        """Assign initial classes to documents"""
        logger.info("Assigning initial classes")

        for doc in collection:
            candidates = self._select_candidates_for_document(
                doc_embedding=doc.embeddings,
                taxonomy_manager=self.taxonomy_manager,
                enriched_classes=enriched_classes,
            )

            logger.info("Candidates for document %s: %s", doc.id, candidates)
            core_classes = self._select_core_classes(
                doc.content, list(candidates))
            doc.initial_core_classes = set(core_classes)
            logger.info("Assigned classes for document %s: %s",
                        doc.id, core_classes)

        return collection

    def _select_core_classes(self, doc: str, candidates: List[str]) -> List[str]:
        """
        Select core classes from a list of candidates using LLM
        """
        try:
            prompt = f"""Given this document:
"{doc}"

And these possible classes:
{', '.join(candidates)}

Select ONLY the most specific and directly relevant classes that best describe the main topics of this document.
Important guidelines:
- Choose classes that are most specific to the document's content
- Exclude broad/general classes unless they are directly discussed
- Do not include parent classes unless they are explicitly relevant
- Focus on 2-3 most relevant classes maximum
- If uncertain about a class, exclude it

Return only the selected class names separated by commas, nothing else."""

            response = self.llm.chat(
                model="llama3.2:3b-instruct-fp16",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
            )

            if not response:
                logger.warning(
                    "Empty response from LLM for core classes selection")
                return []

            core_classes = response["message"]["content"].strip().split(",")
            logger.info("Selected core classes: %s", core_classes)

            return [cls.strip() for cls in core_classes]

        except Exception as e:
            logger.error("Error selecting core classes: %s", str(e))
            return []

    def get_class_terms(self) -> Dict[str, EnrichedClass]:
        """Return the enriched terms and their embeddings"""
        return self.class_terms

    def _select_candidates_for_document(
        self,
        doc_embedding: np.ndarray,
        taxonomy_manager: TaxonomyManager,
        enriched_classes: Dict[str, EnrichedClass],
    ) -> Set[str]:
        """Select candidate classes for a document using level-wise traversal"""
        candidates = set()
        current_level = set(taxonomy_manager.root_nodes)

        logger.info("Taxonomy max depth is %d", taxonomy_manager.max_depth + 1)
        for level in range(taxonomy_manager.max_depth + 1):
            if not current_level:
                break

            # Calculate similarities for current level
            similarities = [
                (node, self._compute_similarity(
                    doc_embedding, enriched_classes[node]))
                for node in current_level
            ]

            # Select top candidates
            similarities.sort(key=lambda x: x[1], reverse=True)
            selected = {node for node, _ in similarities[: level + 2]}
            candidates.update(selected)

            # Prepare next level
            current_level = {
                child
                for node in selected
                for child in taxonomy_manager.taxonomy.successors(node)
            }
            logger.info("Candidates at level %d: %s", level, selected)

        return candidates

    def _compute_similarity(
        self, embedding: np.ndarray, enriched_class: EnrichedClass
    ) -> float:
        """Compute similarity between a document and an enriched class"""
        if enriched_class is None:
            logger.error("enriched_class is None")
            return 0.0

        if not hasattr(enriched_class, "embeddings"):
            logger.error("Class %s has no embeddings attribute",
                         enriched_class.terms)
            return 0.0

        if enriched_class.embeddings is None:
            logger.error("Class %s has None embeddings", enriched_class.terms)
            return 0.0

        if embedding is None:
            logger.error("Document embedding is None")
            return 0.0

        return np.max(
            np.dot(enriched_class.embeddings, embedding)
            / (
                np.linalg.norm(enriched_class.embeddings, axis=1)
                * np.linalg.norm(embedding)
            )
        )


if __name__ == "__main__":
    llm = Client("http://192.168.1.91:11434")
    G = DiGraph()
    G.add_edges_from(
        [
            ("domain", "mobility"),
            ("domain", "health"),
            # ("domain", "information technology"),
            ("domain", "energy"),
            ("domain", "environment"),
            # ("domain", "trade"),
            ("domain", "construction"),
            ("domain", "culture"),
            ("domain", "administration"),
            ("domain", "urban planning"),
            ("domain", "education"),
            ("mobility", "environmental monitoring"),
            ("mobility", "public transport"),
            ("mobility", "shared mobility"),
            ("mobility", "traffic management"),
            ("mobility", "vehicle infrastructure"),
            ("environment", "weather monitoring"),
            ("environment", "air quality monitoring"),
        ]
    )

    enricher = LLMEnricher(llm, G)
    enricher.enrich_classes_with_terms()
    enricher.get_class_terms()
