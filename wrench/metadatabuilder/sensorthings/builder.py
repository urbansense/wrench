from itertools import batched
from typing import Any, Sequence

from wrench.metadatabuilder.base import BaseMetadataBuilder
from wrench.metadatabuilder.sensorthings.querybuilder import (
    CombinedFilter,
    FilterOperator,
    ThingQuery,
)
from wrench.models import CommonMetadata, Device, Group
from wrench.utils.generator import Content, ContentGenerator, GeneratorConfig

from .spatial import (
    GeometryCollector,
    PolygonalExtentCalculator,
)


class SensorThingsMetadataBuilder(BaseMetadataBuilder):
    def __init__(
        self,
        base_url: str,
        title: str,
        description: str,
        generator_config: GeneratorConfig | dict[str, Any],
    ):
        """
        Builds metadata for SensorThings API entries.

        Args:
            base_url (str): Base SensorThings URL to harvest items from.
            title (str): Title to use for generating entries in the catalog.
            description (str): Description to use for generating entries in the catalog.
            generator_config (dict[str, Any]): Config for content generator for
                generating name and description for device group metadata
        """
        super().__init__()

        self.base_url = base_url
        self.title = title
        self.description = description

        if isinstance(generator_config, dict):
            generator_config = GeneratorConfig.model_validate(generator_config)

        self.content_generator = ContentGenerator(generator_config)
        self.service_spatial_calculator = PolygonalExtentCalculator()
        self.group_spatial_calculator = GeometryCollector()

    def build_service_metadata(self, devices: Sequence[Device]) -> CommonMetadata:
        """
        Retrieves metadata for the SensorThings data.

        This method collects the locations of each 'thing' and calculates the geographic
        extent and timeframe for the data. It then returns a CommonMetadata object
        populated with this information.

        Returns:
            CommonMetadata: An object containing metadata such as endpoint URL, title,
                            identifier, description, spatial extent, temporal extent,
                            source type, and last updated time.
        """
        geographic_extent = self.service_spatial_calculator.calculate_extent(devices)

        timeframe = self._calculate_timeframe(devices)

        self.metadata = CommonMetadata(
            endpoint_urls=[self.base_url],
            title=self.title,
            identifier=self.title.lower().strip().replace(" ", "_"),
            description=self.description,
            spatial_extent=str(geographic_extent),
            temporal_extent=timeframe,
            source_type="sensorthings",
            last_updated=timeframe.latest_time,
        )

        return self.metadata

    def build_group_metadata(
        self, group: Group, title: str | None = None, description: str | None = None
    ) -> CommonMetadata:
        """
        Groups a list of Devices and builds their metadata.

        Args:
            group (Group): The group returned from a Grouper.
            title (str | None): Optional title if provided
            description (str | None): Optional description if provided

        Returns:
            metadata (CommonMetadata): CommonMetadata extracted
                from the groups
        """
        geographic_extent = self.group_spatial_calculator.calculate_extent(
            group.devices
        )

        timeframe = self._calculate_timeframe(group.devices)

        endpoint_urls = self._build_group_url(group.devices)

        if not title or not description:
            content = self.content_generator.generate_group_content(
                group,
                context={
                    "service_metadata": self.metadata,
                },
            )
        else:
            content = Content(name=title, description=description)

        return CommonMetadata(
            identifier=content.name.lower().strip().replace(" ", "_"),
            title=content.name,
            description=content.description,
            endpoint_urls=endpoint_urls,
            tags=list(group.parent_classes),
            source_type="sensorthings",
            temporal_extent=timeframe,
            spatial_extent=str(geographic_extent),
            last_updated=timeframe.latest_time,
            thematic_groups=[
                parent.lower().replace(" ", "-") for parent in group.parent_classes
            ],
        )

    def _build_group_url(self, devices: list[Device]) -> list[str]:
        """
        Builds resource URL for groups.

        Takes the ID of each Thing and filters the base URL based on them. Each URL is
        only limited to 100 Things to keep the URL length manageable.

        Args:
            devices (list[Device]): List of devices belonging to a group.

        Returns:
            url (list[str]): The list of resource URLs with the ID of Devices filtered.
        """
        if not devices:
            raise ValueError("Device list is empty, cannot build URL")

        urls = []
        chunk_size = 100

        for device_chunk in batched(devices, chunk_size):
            filters = [
                ThingQuery.property("@iot.id").eq(device.id) for device in device_chunk
            ]
            if filters:
                filter_expression = CombinedFilter(FilterOperator.OR, filters)
            else:
                raise ValueError("Filters is empty, check if @iot.id exists")

            query = ThingQuery().filter(filter_expression).build()

            urls.append(f"{self.base_url}/{query}")

        return urls
