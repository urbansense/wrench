from typing import Any

from wrench.harvester.base import BaseHarvester
from wrench.harvester.sensorthings.translator import TranslationService
from wrench.models import Item

from .client import SensorThingsClient
from .config import PaginationConfig, TranslatorConfig
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
        pagination_config: PaginationConfig | dict[str, Any] = {},
        translator_config: TranslatorConfig | dict[str, Any] = {},
    ):
        """
        Initialize the harvester.

        Args:
            base_url (str): Base SensorThings URL to harvest items from.
            title (str): Title of the entry in the catalog.
            description (str): Description of the entry in the catalog.
            pagination_config (PaginationConfig | dict[str, Any]): Pagination config
                for fetching items.
            translator_config (TranslationConfig | None): Optional translator config.
        """
        if pagination_config:
            if isinstance(pagination_config, dict):
                pagination_config = PaginationConfig.model_validate(pagination_config)

        self.client = SensorThingsClient(base_url=base_url, config=pagination_config)

        if translator_config:
            if isinstance(translator_config, dict):
                translator_config = TranslatorConfig.model_validate(translator_config)

        self.translator = TranslationService.from_config(translator_config)

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

    def return_items(self) -> list[Item]:
        """Returns things."""
        things = self.fetch_items()
        return [
            Item(id=thing.id, content=thing.model_dump(mode="json")) for thing in things
        ]
