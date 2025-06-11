from datetime import datetime
from typing import Any

from wrench.harvester.base import BaseHarvester
from wrench.harvester.sensorthings.translator import TranslationService
from wrench.models import Device, TimeFrame

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
            pagination_config (PaginationConfig | dict[str, Any]): Pagination config
                for fetching items.
            translator_config (TranslationConfig | dict[str, Any]): Translator config.
        """
        super().__init__()
        pagination_config = PaginationConfig.model_validate(pagination_config)
        translator_config = TranslatorConfig.model_validate(translator_config)

        self.client = SensorThingsClient(base_url, pagination_config)

        self.translator = TranslationService.from_config(translator_config)

    def fetch_items(self) -> list[Thing]:
        """
        Fetches items with optional translation.

        Returns:
            things (list[Thing]) : List of things, translated if translation
                is configured.
        """
        things = self.client.fetch_things()

        if not self.translator:
            return things

        return [self.translator.translate(thing) for thing in things]

    def return_items(self) -> list[Device]:
        """Returns things."""
        things = self.fetch_items()

        devices = []

        for thing in things:
            time_frame = None
            for ds in thing.datastreams:
                if ds.phenomenon_time:
                    start_time = datetime.fromisoformat(
                        ds.phenomenon_time.split("/")[0]
                    )
                    latest_time = datetime.fromisoformat(
                        ds.phenomenon_time.split("/")[1]
                    )
                    time_frame = TimeFrame(
                        start_time=start_time, latest_time=latest_time
                    )

            device = Device(
                id=thing.id,
                name=thing.name,
                description=thing.description,
                locations=thing.location,
                time_frame=time_frame,
                datastreams={ds.name for ds in thing.datastreams},
                sensor_names={ds.sensor.name for ds in thing.datastreams},
                observed_properties={
                    ds.observed_property.name for ds in thing.datastreams
                },
                properties=thing.properties,
                _raw_data=thing.model_dump(),
            )

            devices.append(device)

        return devices
