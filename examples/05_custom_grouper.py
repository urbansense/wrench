"""
Example: Custom grouper
Demonstrates: How to implement a custom grouper by subclassing BaseGrouper.
              The example grouper assigns devices to groups based on a keyword
              found in the device name — no ML dependencies required.
Prerequisites: pip install auto-wrench
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

import geojson

from wrench.cataloger.noop import NoopCataloger
from wrench.grouper.base import BaseGrouper
from wrench.harvester.base import BaseHarvester
from wrench.metadataenricher.sensorthings import SensorThingsMetadataEnricher
from wrench.models import Device, Group, Location, TimeFrame
from wrench.pipeline.sensor_pipeline import SensorRegistrationPipeline
from wrench.utils.config import LLMConfig

# ---------------------------------------------------------------------------
# Custom grouper implementation
# ---------------------------------------------------------------------------


class KeywordGrouper(BaseGrouper):
    """Groups devices by matching keywords in their names.

    Each keyword in `keyword_to_group` maps to a group name. A device is
    assigned to the first matching group. Devices that match no keyword are
    collected in the "Uncategorized" group.

    This grouper demonstrates the minimal contract required by BaseGrouper:
    implement `group_devices(devices) -> list[Group]`.
    """

    def __init__(self, keyword_to_group: dict[str, str]) -> None:
        """
        Args:
            keyword_to_group: Mapping of lowercase keyword → group name.
                              Example: {"air": "Air Quality", "traffic": "Mobility"}
        """
        # keyword_to_group maps keyword → group label
        self.keyword_to_group = {k.lower(): v for k, v in keyword_to_group.items()}

    def group_devices(self, devices: list[Device], **kwargs) -> list[Group]:
        """Assign each device to a group based on keyword matching.

        Args:
            devices: Devices returned by the harvester.
            **kwargs: Ignored — reserved for future use by the base class.

        Returns:
            list[Group]: One Group per matched keyword, plus an "Uncategorized"
                         group for any devices that did not match.
        """
        buckets: dict[str, list[Device]] = defaultdict(list)

        for device in devices:
            matched = False
            name_lower = device.name.lower()
            for keyword, group_name in self.keyword_to_group.items():
                if keyword in name_lower:
                    buckets[group_name].append(device)
                    matched = True
                    break
            if not matched:
                buckets["Uncategorized"].append(device)

        groups = []
        for group_name, group_devices in buckets.items():
            if group_devices:
                groups.append(
                    Group(
                        name=group_name,
                        devices=group_devices,
                        # parent_classes can carry thematic taxonomy labels.
                        # Leave empty if not applicable.
                        parent_classes=set(),
                    )
                )

        return groups


# ---------------------------------------------------------------------------
# Minimal stub harvester to make this example self-contained
# ---------------------------------------------------------------------------


class StubHarvester(BaseHarvester):
    """Returns a hardcoded list of devices."""

    def return_devices(self) -> list[Device]:
        now = datetime.now(tz=timezone.utc)
        location = Location(
            encoding_type="application/geo+json",
            location=geojson.Point((11.576, 48.137)),
        )
        time_frame = TimeFrame(start_time=now, latest_time=now)

        return [
            Device(
                id="d1",
                name="Air Quality Monitor Downtown",
                description="Measures PM2.5 levels.",
                datastreams={"PM2.5"},
                sensors={"Alphasense OPC"},
                observed_properties={"Particulate Matter"},
                locations=[location],
                time_frame=time_frame,
            ),
            Device(
                id="d2",
                name="Traffic Counter North Bridge",
                description="Counts vehicles crossing the bridge.",
                datastreams={"Vehicle Count"},
                sensors={"Inductive Loop"},
                observed_properties={"Vehicle Count"},
                locations=[location],
                time_frame=time_frame,
            ),
            Device(
                id="d3",
                name="Noise Sensor Market Square",
                description="Continuous urban noise monitoring.",
                datastreams={"LAeq"},
                sensors={"NTi XL2"},
                observed_properties={"Sound Pressure Level"},
                locations=[location],
                time_frame=time_frame,
            ),
        ]


# ---------------------------------------------------------------------------
# Wire into pipeline
# ---------------------------------------------------------------------------


async def main() -> None:
    grouper = KeywordGrouper(
        keyword_to_group={
            "air quality": "Air Quality",
            "traffic": "Mobility",
            "noise": "Noise",
        }
    )

    llm_config = LLMConfig(
        base_url="http://localhost:11434/v1",
        model="llama3.3:70b-instruct-q4_K_M",
    )

    pipeline = SensorRegistrationPipeline(
        harvester=StubHarvester(),
        grouper=grouper,
        metadataenricher=SensorThingsMetadataEnricher(
            base_url="https://example.org/v1.1",
            title="Stub Sensor Network",
            description="Example network for demonstrating a custom grouper.",
            llm_config=llm_config,
        ),
        cataloger=NoopCataloger(),
    )

    result = await pipeline.run_async()
    print(f"Pipeline succeeded: {result.success}")


if __name__ == "__main__":
    asyncio.run(main())
