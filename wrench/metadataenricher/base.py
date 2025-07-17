from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from wrench.log import logger
from wrench.models import CommonMetadata, Device, Group, TimeFrame
from wrench.utils.config import LLMConfig
from wrench.utils.sanitization import sanitize_ckan_name

from .generator import Content, ContentGenerator


class BaseMetadataEnricher(ABC):
    def __init__(
        self, title: str, description: str, llm_config: LLMConfig | None = None
    ):
        """
        Base metadata enricher with generic functionality.

        Args:
            title: Service title for metadata
            description: Service description for metadata
            llm_config: Optional config for content generation
        """
        self.logger = logger.getChild(self.__class__.__name__)
        self.title = title
        self.description = description

        if llm_config:
            self.content_generator = ContentGenerator(llm_config)

    def build_service_metadata(self, devices: list[Device]) -> CommonMetadata:
        """
        Generic service metadata building with spatial and temporal enrichment.

        Args:
            devices: List of Device objects to build metadata from

        Returns:
            CommonMetadata: Enriched metadata for the service
        """
        geographic_extent = self._calculate_service_spatial_extent(devices)
        timeframe = self._calculate_timeframe(devices)

        self.metadata = CommonMetadata(
            endpoint_urls=self._build_service_urls(devices),
            title=self.title,
            identifier=sanitize_ckan_name(self.title, fallback_prefix="service"),
            description=self.description,
            spatial_extent=str(geographic_extent),
            temporal_extent=timeframe,
            source_type=self._get_source_type(),
            last_updated=timeframe.latest_time,
        )

        return self.metadata

    def build_group_metadata(
        self, group: Group, title: str | None = None, description: str | None = None
    ) -> CommonMetadata:
        """
        Generic group metadata building with spatial, temporal, and content enrichment.

        Args:
            group: The group returned from a Grouper
            title: Optional title override
            description: Optional description override

        Returns:
            CommonMetadata: Enriched metadata for the group
        """
        geographic_extent = self._calculate_group_spatial_extent(group.devices)
        timeframe = self._calculate_timeframe(group.devices)
        endpoint_urls = self._build_group_urls(group.devices)

        # Generate content if not provided and generator available
        if not title or not description:
            if self.content_generator and hasattr(self, "metadata"):
                content = self.content_generator.generate_group_content(
                    group, context={"service_metadata": self.metadata}
                )
            else:
                # Fallback to basic naming using group.name
                content = Content(
                    name=title or group.name or "Unnamed Group",
                    description=description or "Auto-generated device group",
                )
        else:
            content = Content(name=title, description=description)

        return CommonMetadata(
            identifier=sanitize_ckan_name(content.name, fallback_prefix="group"),
            title=content.name,
            description=content.description,
            endpoint_urls=endpoint_urls,
            tags=list(group.parent_classes),
            source_type=self._get_source_type(),
            temporal_extent=timeframe,
            spatial_extent=str(geographic_extent),
            last_updated=timeframe.latest_time,
            thematic_groups=[
                parent.lower().replace(" ", "-") for parent in group.parent_classes
            ],
        )

    @abstractmethod
    def _get_source_type(self) -> str:
        """Return the source type identifier."""
        pass

    @abstractmethod
    def _build_service_urls(self, devices: list[Device]) -> list[str]:
        """Build service endpoint URLs."""
        pass

    @abstractmethod
    def _build_group_urls(self, devices: list[Device]) -> list[str]:
        """Build group-specific resource URLs."""
        pass

    @abstractmethod
    def _calculate_service_spatial_extent(self, devices: list[Device]) -> Any:
        """Calculate service spatial extent for devices."""
        pass

    @abstractmethod
    def _calculate_group_spatial_extent(self, devices: list[Device]) -> Any:
        """Calculate group spatial extent for devices."""
        pass

    def _calculate_timeframe(self, devices: list[Device]) -> TimeFrame:
        """
        Calculate the overall timeframe spanning all sensor data.

        Args:
            devices: List of Device objects.

        Returns:
            TimeFrame: Object containing the earliest start time and latest end time

        Notes:
            - Handles ISO format datetime strings from phenomenon_time
            - All times are converted to UTC timezone
            - Skips datastreams with no phenomenon_time
        """
        # Initialize timeframe boundaries
        time_bounds = {
            "earliest": datetime.max.replace(tzinfo=timezone.utc),
            "latest": datetime.min.replace(tzinfo=timezone.utc),
        }

        # Process each datastream's phenomenon time
        for device in devices:
            # Update overall boundaries
            if not device.time_frame:
                self.logger.warning("Device %s has no time_frame", device.id)
                continue

            time_bounds["earliest"] = min(
                time_bounds["earliest"], device.time_frame.start_time
            )
            time_bounds["latest"] = max(
                time_bounds["latest"], device.time_frame.latest_time
            )

        return TimeFrame(
            start_time=time_bounds["earliest"], latest_time=time_bounds["latest"]
        )
