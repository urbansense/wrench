from typing import TYPE_CHECKING, Optional

from autoreg_metadata.log import logger

# Use TYPE_CHECKING for imports needed only for type hints
if TYPE_CHECKING:
    from autoreg_metadata.catalogger.base import BaseCatalogger
    from autoreg_metadata.grouper.base import BaseGrouper
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
        grouper: Optional["BaseGrouper"] = None,
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
        self.grouper = grouper
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self):
        """
        Execute the pipeline with available components.
        Returns PipelineResult containing execution results or None if failed.
        """
        self.logger.info(
            "Running pipeline with %s harvester, %s classifier, and %s catalogger...",
            self.harvester.__class__.__name__,
            self.grouper.__class__.__name__,
            self.catalogger.__class__.__name__,
        )
        try:
            # Step 1: Harvest data
            self.logger.debug("Retrieving data with harvester")
            service_metadata = self.harvester.get_metadata()
            documents = self.harvester.get_items()
            if not service_metadata or not documents:
                self.logger.warning("No data retrieved from harvester")
                return None

            # Step 2: Optional classification
            grouped_docs = None
            if self.grouper is not None:
                self.logger.debug("Starting classification")
                try:
                    grouped_docs = self.grouper.group_documents(documents)
                except Exception as e:
                    self.logger.error("Classification failed: %s", e)
                    # Continue pipeline even if classification fails

            # Step 3: Catalog results
            try:
                # If classification was performed and successful, use classified documents
                # Otherwise, use raw documents in a default structure
                docs_to_catalog = grouped_docs or {}

                self.logger.debug("Registering data into catalog")
                self.catalogger.register(service_metadata, docs_to_catalog)
            except Exception as e:
                self.logger.error("Cataloging failed: %s", e)
                # Still return results even if cataloging fails

        except Exception as e:
            self.logger.error("Pipeline execution failed: %s", e)
            raise