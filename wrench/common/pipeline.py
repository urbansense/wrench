from typing import Optional

from wrench.cataloger.base import BaseCataloger
from wrench.grouper.base import BaseGrouper
from wrench.harvester.base import BaseHarvester
from wrench.log import logger
from wrench.metadatabuilder.base import BaseMetadataBuilder


class Pipeline:
    """
    A composable pipeline for processing sensor data.

    Components can be added or omitted based on requirements.
    """

    def __init__(
        self,
        harvester: BaseHarvester,
        cataloger: BaseCataloger,
        metadata_builder: BaseMetadataBuilder,
        grouper: Optional[BaseGrouper] = None,
    ):
        """
        Initialize the pipeline with the given components.

        Args:
            harvester (BaseHarvester): The harvester component responsible for data collection.
            cataloger (BaseCataloger): The cataloger component responsible for cataloging data.
            grouper (Optional[BaseGrouper], optional): The grouper component for grouping data.
            metadata_builder (BaseMetadataBuilder): The metadata builder used to build metadata.
        """
        self.harvester = harvester
        self.cataloger = cataloger
        self.grouper = grouper
        self.metadata_builder = metadata_builder
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self):
        """Execute the pipeline with available components."""
        self.logger.info(
            "Running pipeline with %s harvester, %s classifier, %s metadata builder, and %s cataloger...",
            self.harvester.__class__.__name__,
            self.grouper.__class__.__name__ if self.grouper else "No",
            self.metadata_builder.__class__.__name__,
            self.cataloger.__class__.__name__,
        )

        items_processed = 0

        try:
            # Step 1: Harvest data
            self.logger.debug("Retrieving data with harvester")

            all_items = self.harvester.return_items()

            self.logger.info("Building metadata with builder")
            service_metadata = self.metadata_builder.build_service_metadata(all_items)

            if not all_items:
                self.logger.warning("No data retrieved from harvester")
                return False, 0

            else:
                items_to_process = all_items
                self.logger.info(f"Processing all {len(all_items)} items")

            items_processed = len(items_to_process)

            # Step 3: Optional classification
            new_groups = []
            if self.grouper is not None and items_to_process:
                self.logger.debug("Grouping %d items", len(items_to_process))
                try:
                    new_groups = self.grouper.group_items(items_to_process)
                    self.logger.info(f"Created {len(new_groups)} groups from new items")
                except Exception as e:
                    self.logger.error("Classification failed: %s", e)
                    # Continue pipeline even if classification fails

            # Step 4: Generate metadata for groups
            group_metadata = [
                self.metadata_builder.build_group_metadata(group)
                for group in new_groups
                if new_groups
            ]

            # Step 6: Catalog results
            try:
                self.logger.debug("Registering data into catalog")
                self.cataloger.register(service_metadata, group_metadata)
            except Exception as e:
                self.logger.error("Cataloging failed: %s", e)
                return False, items_processed

        except Exception as e:
            self.logger.error("Pipeline execution failed: %s", e)
            raise
