from autoreg_metadata.log import logger
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING for imports needed only for type hints
if TYPE_CHECKING:
    from autoreg_metadata.catalogger.base import BaseCatalogger
    from autoreg_metadata.classifier.base import BaseClassifier
    from autoreg_metadata.harvester.base import BaseHarvester


class Pipeline:
    """
    A composable pipeline for processing sensor data.
    Components can be added or omitted based on requirements.
    """

    def __init__(
        self,
        harvester: "BaseHarvester",
        catalogger: "BaseCatalogger",
        classifier: Optional["BaseClassifier"] = None
    ):
        """
        Initialize pipeline with required and optional components.

        Args:
            harvester: Component for harvesting sensor data
            catalogger: Component for cataloging results
            classifier: Optional component for classification
        """
        self.harvester = harvester
        self.catalogger = catalogger
        self.classifier = classifier
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self):
        """
        Execute the pipeline with available components.
        Returns PipelineResult containing execution results or None if failed.
        """
        try:
            # Step 1: Harvest data
            metadata, documents = self.harvester.enrich()
            if not metadata or not documents:
                self.logger.warning("No data retrieved from harvester")
                return None

            # Step 2: Optional classification
            classified_docs = None
            if self.classifier is not None:
                try:
                    classified_docs = self.classifier.classify_documents(
                        documents)
                except Exception as e:
                    self.logger.error("Classification failed: %s", e)
                    # Continue pipeline even if classification fails

            # Step 3: Catalog results
            try:
                # If classification was performed and successful, use classified documents
                # Otherwise, use raw documents in a default structure
                docs_to_catalog = classified_docs if classified_docs is not None else {}

                self.catalogger.register(metadata, docs_to_catalog)
            except Exception as e:
                self.logger.error("Cataloging failed: %s", e)
                # Still return results even if cataloging fails

        except Exception as e:
            self.logger.error("Pipeline execution failed: %s", e)
            return None
