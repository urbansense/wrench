from wrench.grouper.base import Group
from wrench.harvester.base import BaseHarvester, TranslationService
from wrench.models import CommonMetadata
from wrench.utils import ContentGenerator

from .client import SensorThingsClient
from .config import PaginationConfig
from .metadata.builder import MetadataBuilder
from .metadata.spatial import (
    GeometryCollector,
    PolygonalExtentCalculator,
)
from .models import Thing


class SensorThingsHarvester(BaseHarvester):
    """
    Harvests SensorThings API entities.

    Returns metadata and list of items contained in the
    API server
    """

    def __init__(
        self,
        base_url: str,
        title: str,
        description: str,
        content_generator: ContentGenerator,
        pagination_config: PaginationConfig | None = None,
        translator: TranslationService | None = None,
    ):
        """
        Initialize the harvester.

        Args:
            base_url (str): Base SensorThings URL to harvest items from.
            title (str): Title of the entry in the catalog.
            description (str): Description of the entry in the catalog.
            content_generator (ContentGenerator): Content generator for generating
                    name and description for device group metadata
            pagination_config (PaginationConfig | None): Pagination config
                for fetching items.
            translator (TranslationService | None): Optional translator.
        """
        # Set up translator if configured
        self.client = SensorThingsClient(base_url=base_url, config=pagination_config)

        self.translator = translator

        self.things = self.fetch_items()

        self.metadata_builder = MetadataBuilder(
            base_url=base_url,
            title=title,
            description=description,
            things=self.things,
            content_generator=content_generator,
        )

    def fetch_items(self) -> list[Thing]:
        """
        Fetches items with optional translation.

        Returns:
            things (list[Thing]) : List of things, translated if translation
                is configured.
        """
        things = self.client.fetch_items(limit=20)

        if not self.translator:
            return things

        return [self.translator.translate(thing) for thing in things]

    def return_items(self) -> list[Thing]:
        """Returns things."""
        return self.things

    def get_service_metadata(self) -> CommonMetadata:
        return self.metadata_builder.get_service_metadata(
            spatial_calculator=PolygonalExtentCalculator()
        )

    def get_device_group_metadata(self, group: Group) -> CommonMetadata:
        return self.metadata_builder.get_device_group_metadata(
            group=group, spatial_calculator=GeometryCollector()
        )
