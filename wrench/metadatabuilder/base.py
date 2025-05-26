from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Sequence

from wrench.log import logger
from wrench.models import CommonMetadata, Device, Group, TimeFrame


class BaseMetadataBuilder(ABC):
    def __init__(self):
        """Initializes logger for all subclasses of BaseMetadataBuilder."""
        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def build_service_metadata(self, source_data: Sequence[Device]) -> CommonMetadata:
        """
        Retrieves metadata for service endpoint.

        Returns:
            CommonMetadata: Data model conformant to catalog requirement.
        """
        pass

    @abstractmethod
    def build_group_metadata(self, group: Group) -> CommonMetadata:
        """
        Builds metadata for groups returned by Grouper.

        Returns:
            CommonMetadata: Data model conformant to catalog requirement.
        """
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
