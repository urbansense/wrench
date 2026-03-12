"""
Example: Custom harvester
Demonstrates: How to implement a custom harvester by subclassing BaseHarvester.
              The example harvester reads device data from a local JSON file
              instead of a remote API.
Prerequisites: pip install auto-wrench
"""

import asyncio
from datetime import datetime

import geojson

from wrench.cataloger.noop import NoopCataloger
from wrench.grouper.lda import LDAGrouper
from wrench.grouper.lda.models import LDAConfig
from wrench.harvester.base import BaseHarvester
from wrench.metadataenricher.sensorthings import SensorThingsMetadataEnricher
from wrench.models import Device, Location, TimeFrame
from wrench.pipeline.sensor_pipeline import SensorRegistrationPipeline
from wrench.utils.config import LLMConfig

# ---------------------------------------------------------------------------
# Sample device data used by the custom harvester.
# In a real harvester this data would come from an external API or database.
# ---------------------------------------------------------------------------
SAMPLE_DEVICES = [
    {
        "id": "sensor-001",
        "name": "Air Quality Station Alpha",
        "description": "Measures PM2.5, NO2, and O3 in the city centre.",
        "datastreams": ["PM2.5 Concentration", "NO2 Concentration", "O3 Concentration"],
        "sensors": ["Alphasense OPC-N3", "Alphasense NO2-B43F"],
        "observed_properties": ["Particulate Matter", "Nitrogen Dioxide", "Ozone"],
        "longitude": 11.576124,
        "latitude": 48.137154,
        "start_time": "2023-01-01T00:00:00+00:00",
        "latest_time": "2024-12-31T23:59:59+00:00",
    },
    {
        "id": "sensor-002",
        "name": "Traffic Counter Beta",
        "description": "Counts vehicles and measures average speed on the ring road.",
        "datastreams": ["Vehicle Count", "Average Speed"],
        "sensors": ["Inductive Loop Detector"],
        "observed_properties": ["Vehicle Count", "Speed"],
        "longitude": 11.601,
        "latitude": 48.145,
        "start_time": "2023-03-15T00:00:00+00:00",
        "latest_time": "2024-12-31T23:59:59+00:00",
    },
    {
        "id": "sensor-003",
        "name": "Noise Level Monitor Gamma",
        "description": "Continuous noise level monitoring near the main square.",
        "datastreams": ["Sound Pressure Level (LAeq)", "Sound Pressure Level (LCeq)"],
        "sensors": ["NTi Audio XL2"],
        "observed_properties": ["Sound Pressure Level"],
        "longitude": 11.582,
        "latitude": 48.139,
        "start_time": "2022-06-01T00:00:00+00:00",
        "latest_time": "2024-12-31T23:59:59+00:00",
    },
]


class LocalJSONHarvester(BaseHarvester):
    """Harvester that loads device metadata from an in-memory list.

    In a real implementation you would replace `_load_raw_devices` with
    HTTP requests, database queries, or file I/O as needed.
    """

    def __init__(self, devices: list[dict]) -> None:
        # Always call super().__init__() — it sets up self.logger.
        super().__init__()
        self._raw_devices = devices

    def return_devices(self) -> list[Device]:
        """Convert raw dicts into Device objects and return them.

        This is the only method you must implement. The pipeline calls it
        on every run to obtain the current list of devices.
        """
        self.logger.info("Loading %d devices from local data", len(self._raw_devices))
        devices = []
        for raw in self._raw_devices:
            device = self._parse_device(raw)
            devices.append(device)
        return devices

    # ------------------------------------------------------------------
    # Private helpers — not part of the BaseHarvester contract.
    # ------------------------------------------------------------------

    def _parse_device(self, raw: dict) -> Device:
        """Convert a raw dict into a Device model."""
        location = Location(
            encoding_type="application/geo+json",
            location=geojson.Point((raw["longitude"], raw["latitude"])),
        )
        time_frame = TimeFrame(
            start_time=datetime.fromisoformat(raw["start_time"]),
            latest_time=datetime.fromisoformat(raw["latest_time"]),
        )
        return Device(
            id=raw["id"],
            name=raw["name"],
            description=raw["description"],
            datastreams=set(raw["datastreams"]),
            sensors=set(raw["sensors"]),
            observed_properties=set(raw["observed_properties"]),
            locations=[location],
            time_frame=time_frame,
        )


# ---------------------------------------------------------------------------
# Wire the custom harvester into a pipeline.
# ---------------------------------------------------------------------------


async def main() -> None:
    harvester = LocalJSONHarvester(devices=SAMPLE_DEVICES)

    grouper = LDAGrouper(config=LDAConfig(n_topics=3, use_llm_naming=False))

    llm_config = LLMConfig(
        base_url="http://localhost:11434/v1",
        model="llama3.3:70b-instruct-q4_K_M",
    )

    # SensorThingsMetadataEnricher works with any set of Device objects —
    # you do not need to use a SensorThings harvester with it.
    metadata_enricher = SensorThingsMetadataEnricher(
        base_url="https://example.org/v1.1",  # used as the service endpoint URL
        title="Local Sensor Dataset",
        description="Devices loaded from a local JSON source.",
        llm_config=llm_config,
    )

    pipeline = SensorRegistrationPipeline(
        harvester=harvester,
        grouper=grouper,
        metadataenricher=metadata_enricher,
        cataloger=NoopCataloger(),
    )

    result = await pipeline.run_async()
    print(f"Pipeline succeeded: {result.success}")


if __name__ == "__main__":
    asyncio.run(main())
