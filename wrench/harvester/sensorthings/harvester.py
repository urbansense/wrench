from datetime import datetime
from typing import Any

from wrench.harvester.base import BaseHarvester
from wrench.models import Device, TimeFrame

from .client import SensorThingsClient
from .config import PaginationConfig
from .models import Datastream, MultiDatastream, Thing


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
            time_frame = self._build_timeframes(
                thing.datastreams, thing.multidatastreams
            )
            datastreams, sensors, observed_properties = self._extract_stream(thing)

            device = Device(
                id=thing.id,
                name=thing.name,
                description=thing.description,
                locations=thing.location,
                time_frame=time_frame,
                datastreams=datastreams,
                sensors=sensors,
                observed_properties=observed_properties,
                properties=thing.properties,
                _raw_data=thing.model_dump(),
            )

            devices.append(device)

        return devices

    def _build_timeframes(
        self, ds: list[Datastream], mds: list[MultiDatastream]
    ) -> TimeFrame | None:
        # use datastreams if available, mds if ds isn't available
        streams = mds if not ds and mds else ds
        return self._extract_outer_bounds(streams)

    def _extract_outer_bounds(
        self, streams: list[Datastream] | list[MultiDatastream]
    ) -> TimeFrame | None:
        start_times = []
        end_times = []

        for ds in streams:
            if ds.phenomenon_time:
                parts = ds.phenomenon_time.split("/")
                start_times.append(datetime.fromisoformat(parts[0]))
                end_times.append(datetime.fromisoformat(parts[1]))

        if not start_times:
            return None

        return TimeFrame(start_time=min(start_times), latest_time=max(end_times))

    def _extract_stream(self, thing: Thing) -> tuple[set[str], set[str], set[str]]:
        if thing.datastreams:
            return (
                {ds.name for ds in thing.datastreams},
                {ds.sensor.name for ds in thing.datastreams},
                {ds.observed_property.name for ds in thing.datastreams},
            )

        if thing.multidatastreams:
            return (
                {mds.name for mds in thing.multidatastreams},
                {mds.sensor.name for mds in thing.multidatastreams},
                {
                    op.name
                    for mds in thing.multidatastreams
                    for op in mds.observed_properties
                },
            )

        return set(), set(), set()
