from datetime import datetime
from typing import Any

from wrench.harvester.base import BaseHarvester
from wrench.models import Device, TimeFrame

from .client import SensorThingsClient
from .config import PaginationConfig
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
    ):
        """
        Initialize the harvester.

        Args:
            base_url (str): Base SensorThings URL to harvest items from.
            pagination_config (PaginationConfig | dict[str, Any]): Pagination config
                for fetching items.
        """
        super().__init__()
        pagination_config = PaginationConfig.model_validate(pagination_config)

        self.client = SensorThingsClient(base_url, pagination_config)

    def fetch_items(self) -> list[Thing]:
        """
        Fetches items.

        Returns:
            things (list[Thing]) : List of things.
        """
        things = self.client.fetch_things()

        return things

    def return_devices(self) -> list[Device]:
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
                sensors={ds.sensor.name for ds in thing.datastreams},
                observed_properties={
                    ds.observed_property.name for ds in thing.datastreams
                },
                properties=thing.properties,
                _raw_data=thing.model_dump(),
            )

            devices.append(device)

        return devices
