import numpy as np

from autoreg_metadata.classifier.teleclass.core.embeddings import EmbeddingService
from autoreg_metadata.classifier.teleclass.core.models.enrichment_models import (
    EnrichedClass,
)
from autoreg_metadata.classifier.teleclass.core.taxonomy_manager import TaxonomyManager
from autoreg_metadata.harvester.frost import Thing


class SimilarityClassifier:
    """
    A similarity-based hierarchical classifier that uses class embeddings based on core classes
    to map documents to the taxonomy hierarchy.
    """

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager,
        embedding_service: EmbeddingService,
        enriched_classes: dict[str, EnrichedClass],
    ):
        self.taxonomy_manager = taxonomy_manager
        self.embedding_service = embedding_service
        self.enriched_classes = enriched_classes

        # Create class prototype embeddings from enriched classes
        self.class_embeddings = self._create_class_embeddings()

    def _create_class_embeddings(self) -> dict[str, np.ndarray]:
        """Create prototype embeddings for each class using enriched terms"""
        class_embeddings = {}

        for class_name, enriched_class in self.enriched_classes.items():
            if enriched_class.embeddings is not None:
                # Use pre-computed embeddings if available
                class_embeddings[class_name] = enriched_class.embeddings
            else:
                # Create embedding from class terms
                terms = [term.term for term in enriched_class.terms]
                if terms:
                    # Average the embeddings of all terms
                    term_embeddings = self.embedding_service.get_embeddings(terms)
                    class_embeddings[class_name] = np.mean(term_embeddings, axis=0)
                else:
                    # Fallback to class name embedding
                    class_embeddings[class_name] = (
                        self.embedding_service.get_embeddings(class_name)
                    )

        return class_embeddings

    def _compute_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """Compute cosine similarity between two embeddings"""
        return np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )

    def _assign_to_level(
        self, doc_embedding: np.ndarray, candidate_nodes: set[str], level: int = 0
    ) -> list[str]:
        """
        Assign document to nodes at current level using similarity gap detection.
        Returns the most relevant nodes based on the largest similarity gap.
        """
        # Calculate similarities with candidate nodes
        similarities = []
        for node in candidate_nodes:
            if node in self.class_embeddings:
                sim = self._compute_similarity(
                    doc_embedding, self.class_embeddings[node]
                )
                similarities.append((node, sim))

        # Sort by similarity in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)

        if len(similarities) <= 1:
            return [similarities[0][0]] if similarities else []

        # Log similarities for this level
        print(f"\nLevel {level} similarities:")
        print("-" * 40)
        for node, sim in similarities:
            print(f"{node:<30} {sim:.4f}")
        print("-" * 40)

        if len(similarities) <= 1:
            selected = [similarities[0][0]] if similarities else []
            if selected:
                print(f"Only one candidate at level {level}, selecting: {selected[0]}")
            return selected

        # Return only the top match
        top_node = similarities[0][0]
        print(f"Selected top node: {top_node}")
        print(
            f"Class terms: {[term_score.term for term_score in self.enriched_classes[top_node].terms]}\n"
        )

        return [top_node]

    def predict(self, text: str) -> set[str]:
        """
        Predict classes for a document using similarity-based hierarchical mapping.

        Args:
            text: Input text to classify

        Returns:
            set of predicted class names
        """

        # Get document embedding
        doc_embedding = self.embedding_service.get_embeddings(text)

        assigned_classes = set()
        current_level = 0
        # Start from root
        current_nodes = {self.taxonomy_manager.root_nodes[0]}

        # Traverse hierarchy level by level
        while current_nodes and current_level <= self.taxonomy_manager.max_depth:
            # Get assignments at current level
            assignments = self._assign_to_level(
                doc_embedding, current_nodes, current_level
            )
            if not assignments:
                break

            # Add assignments to results
            assigned_classes.update(assignments)

            # Prepare next level candidates (children of assigned nodes)
            next_nodes = set()
            for node in assignments:
                next_nodes.update(self.taxonomy_manager.taxonomy.successors(node))

            current_nodes = next_nodes
            current_level += 1

        return assigned_classes

    def evaluate(
        self, test_docs: list[dict[str, str]], true_labels: list[set[str]]
    ) -> dict[str, float]:
        """
        Evaluate classifier performance on test documents.

        Args:
            test_docs: list of test documents
            true_labels: list of sets containing true class labels

        Returns:
            dictionary with evaluation metrics
        """
        predictions = []
        for doc in test_docs:
            pred = self.predict(str(doc), model_class=Thing)
            predictions.append(pred)

        # Calculate metrics
        precision = sum(
            len(p.intersection(t)) / len(p) if p else 0
            for p, t in zip(predictions, true_labels)
        ) / len(predictions)
        recall = sum(
            len(p.intersection(t)) / len(t) if t else 0
            for p, t in zip(predictions, true_labels)
        ) / len(predictions)
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if precision + recall > 0
            else 0
        )

        return {"precision": precision, "recall": recall, "f1": f1}
