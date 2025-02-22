import numpy as np
from sentence_transformers import SentenceTransformer

from wrench.grouper.teleclass.core.models import Document, EnrichedClass
from wrench.grouper.teleclass.core.taxonomy_manager import TaxonomyManager
from wrench.log import logger


class SimilarityClassifier:
    """
    A similarity-based hierarchical classifier.

    Uses class embeddings based on core classes
    to map documents to the taxonomy hierarchy.
    """

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager,
        encoder: SentenceTransformer,
        enriched_classes: list[EnrichedClass],
    ):
        """
        Initialize the classifier with the given taxonomy manager, encoder, and enriched classes.

        Args:
            taxonomy_manager (TaxonomyManager): The manager for handling taxonomy-related operations.
            encoder (SentenceTransformer): The encoder used for transforming sentences into embeddings.
            enriched_classes (list[EnrichedClass]): A list of enriched classes to be used for creating class embeddings.
        """
        self.taxonomy_manager = taxonomy_manager
        self.encoder = encoder
        self.enriched_classes = enriched_classes
        self.logger = logger.getChild(self.__class__.__name__)

        # Update class embeddings from enriched classes
        self.class_embeddings = self._create_class_embeddings()

    def _create_class_embeddings(self) -> dict[str, np.ndarray]:
        """
        Update embeddings for each class using enriched terms.

        This method uses pre-computed embeddings if available, or creates new embeddings
        from the terms associated with each class. If no terms are available,it raises
        a RuntimeError indicating the classifier hasn't been trained yet.

        Returns:
            dict[str, np.ndarray]: A dictionary where the keys are class names and the values
            are the corresponding embeddings as numpy arrays.
        """
        class_map: dict[str, np.ndarray] = {}
        for ec in self.enriched_classes:
            if ec.embeddings is not None:
                # Use pre-computed embeddings
                self.logger.debug(
                    "using existing class embeddings",
                )
                class_map[ec.class_name] = ec.embeddings
            else:
                # Create embedding from class terms
                terms = [term.term for term in ec.terms]
                if terms:
                    # Average the embeddings of all terms
                    term_embeddings = self.encoder.encode(terms)
                    ec.embeddings = np.mean(term_embeddings, axis=0)
                    self.logger.debug(
                        "creating average class embeddings from terms through averaging with dimension: %s",
                        ec.embeddings.shape,
                    )
                    class_map[ec.class_name] = ec.embeddings
                else:
                    raise RuntimeError(
                        "Class terms are empty, TELEClass classifier must be trained before prediction"
                    )
        return class_map

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

        for name in candidate_nodes:
            if name in self.class_embeddings:
                sim = self.encoder.similarity(
                    doc_embedding, self.class_embeddings[name]
                ).numpy()
                similarities.append((name, sim))

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
                    "only one candidate at level %d, selecting: %s", level, selected[0]
                )
            return selected

        # Return only the top match
        top_node = similarities[0][0]
        self.logger.info("selected top node: %s", top_node)

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
        doc_embedding = self.encoder.encode(text, convert_to_numpy=True)

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
        self, test_docs: list[Document], true_labels: list[set[str]]
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
            self.logger.debug("predictions for document %s: %s", doc.id, pred)
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
