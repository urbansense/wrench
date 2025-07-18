from itertools import batched
from typing import Any

from pydantic import validate_call

from wrench.metadataenricher.base import BaseMetadataEnricher
from wrench.metadataenricher.generator import LLMConfig
from wrench.metadataenricher.sensorthings.querybuilder import (
    CombinedFilter,
    FilterOperator,
    ThingQuery,
)
from wrench.models import Device

from .spatial import (
    GeometryCollector,
    PolygonalExtentCalculator,
)


class SensorThingsMetadataEnricher(BaseMetadataEnricher):
    @validate_call
    def __init__(
        self, base_url: str, title: str, description: str, llm_config: LLMConfig
    ):
        """
        SensorThings-specific metadata enricher.

        Args:
            base_url: Base SensorThings URL to harvest items from
            title: Title to use for generating entries in the catalog
            description: Description to use for generating entries in the catalog
            llm_config: Optional config for content generator
        """
        super().__init__(title, description, llm_config)
        self.base_url = base_url.rstrip("/")

        # SensorThings-specific spatial calculators
        self.service_spatial_calculator = PolygonalExtentCalculator()
        self.group_spatial_calculator = GeometryCollector()

    def _get_source_type(self) -> str:
        """Return SensorThings source type."""
        return "sensorthings"

    def _build_service_urls(self, devices: list[Device]) -> list[str]:
        """For SensorThings, service URL is just the base URL."""
        return [self.base_url]

    def _calculate_service_spatial_extent(self, devices: list[Device]) -> Any:
        """Calculate service spatial extent using SensorThings-specific calculators."""
        return self.service_spatial_calculator.calculate_extent(devices)

    def _calculate_group_spatial_extent(self, devices: list[Device]) -> Any:
        """Calculate group spatial extent using SensorThings-specific calculators."""
        return self.group_spatial_calculator.calculate_extent(devices)

    def _build_group_urls(self, devices: list[Device]) -> list[str]:
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
