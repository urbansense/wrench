import numpy as np

from autoreg_metadata.grouper.teleclass.core.embeddings import EmbeddingService
from autoreg_metadata.grouper.teleclass.core.models.enrichment_models import (
    EnrichedClass,
)
from autoreg_metadata.grouper.teleclass.core.taxonomy_manager import TaxonomyManager
from autoreg_metadata.log import logger


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
        self.logger = logger.getChild(self.__class__.__name__)

        # Create class prototype embeddings from enriched classes
        self.class_embeddings = self._create_class_embeddings()

    def _create_class_embeddings(self) -> dict[str, np.ndarray]:
        """
        Create prototype embeddings for each class using enriched terms.

        This method generates embeddings for each class by either using pre-computed
        embeddings if available, or by creating new embeddings from the terms associated
        with each class. If no terms are available, it falls back to using the class name
        for generating the embedding.

        Returns:
            dict[str, np.ndarray]: A dictionary where the keys are class names and the values
            are the corresponding embeddings as numpy arrays.
        """
        class_embeddings = {}

        for class_name, enriched_class in self.enriched_classes.items():
            if enriched_class.embeddings is not None:
                # Use pre-computed embeddings if available
                class_embeddings[class_name] = np.mean(
                    enriched_class.embeddings, axis=0
                )
                self.logger.info(
                    "Using existing class embeddings with dimension: %s",
                    class_embeddings[class_name].shape,
                )
            else:
                # Create embedding from class terms
                terms = [term.term for term in enriched_class.terms]
                if terms:
                    # Average the embeddings of all terms
                    term_embeddings = self.embedding_service.get_embeddings(terms)
                    class_embeddings[class_name] = np.mean(term_embeddings, axis=0)
                    self.logger.info(
                        "Create average class embeddings from terms through averaging with dimension: %s",
                        class_embeddings[class_name].shape,
                    )
                else:
                    # Fallback to class name embedding
                    class_embeddings[class_name] = (
                        self.embedding_service.get_embeddings(class_name)
                    )
                    self.logger.info(
                        "Create average class embeddings from class name through averaging with dimension: %s",
                        class_embeddings[class_name].shape,
                    )
        return class_embeddings

    def _assign_to_level(
        self, doc_embedding: np.ndarray, candidate_nodes: set[str], level: int = 0
    ) -> list[str]:
        """
        Assign document to nodes at the current level using similarity gap detection.

        This method calculates the similarity between the document embedding and the
        embeddings of candidate nodes. It then selects the most relevant nodes based
        on the largest similarity gap.

        Args:
            doc_embedding (np.ndarray): The embedding of the document to be classified.
            candidate_nodes (set[str]): A set of candidate node identifiers to which
                                        the document could be assigned.
            level (int, optional): The current level in the hierarchy. Defaults to 0.

        Returns:
            list[str]: A list containing the most relevant node identifier(s) based
                       on the similarity gap detection.
        """
        # Calculate similarities with candidate nodes
        similarities = []
        for node in candidate_nodes:
            if node in self.class_embeddings:
                sim = self.embedding_service.encoder.similarity(
                    doc_embedding, self.class_embeddings[node]
                )
                similarities.append((node, sim))

        # Sort by similarity in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)

        if len(similarities) <= 1:
            return [similarities[0][0]] if similarities else []

        # Log similarities for this level
        self.logger.info("Level %s similarities:", level)
        self.logger.info("-" * 40)
        for node, sim in similarities:
            self.logger.info("%-30s %.4f", node, sim)
        self.logger.info("-" * 40)

        if len(similarities) <= 1:
            selected = [similarities[0][0]] if similarities else []
            if selected:
                self.logger.info(
                    "Only one candidate at level %d, selecting: %s", level, selected[0]
                )
            return selected

        # Return only the top match
        top_node = similarities[0][0]
        self.logger.info("Selected top node: %s", top_node)
        self.logger.info(
            "Class terms: %s\n",
            [term_score.term for term_score in self.enriched_classes[top_node].terms],
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
        current_nodes = set(self.taxonomy_manager.root_nodes)

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
        self, test_docs: list[dict[str, any]], true_labels: list[set[str]]
    ) -> dict[str, float]:
        """
        Evaluate classifier performance on test documents.

        Args:
            test_docs: list of test documents
            true_labels: list of sets containing true class labels

        Returns:
            dictionary with evaluation metrics
        """
        self.logger.info("Evaluating model")
        predictions = []
        for doc in test_docs:
            pred = self.predict(doc.content)
            self.logger.debug("Predictions for document %s: %s", doc.id, pred)
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
