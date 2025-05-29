import hashlib
import json
from typing import Any, Sequence

from pydantic import validate_call

from wrench.components.types import Items
from wrench.exceptions import HarvesterError
from wrench.harvester import BaseHarvester
from wrench.log import logger
from wrench.models import Device
from wrench.pipeline.types import (
    Component,
    Operation,
    OperationType,
)


class Harvester(Component):
    """Harvester that determines operations by comparing with previous state."""

    def __init__(self, harvester: BaseHarvester):
        self._harvester = harvester
        self.logger = logger.getChild(self.__class__.__name__)

    @validate_call
    async def run(self, state: dict[str, Any] = {}) -> Items:
        """
        Run the harvester and detect changes compared to previous run.

        Returns:
            Items: Current devices and operations (add/update/delete) since last run

        Raises:
            HarvesterError: If there's an issue retrieving items from the harvester
        """
        previous_devices = state.get("previous_devices")

        try:
            # Fetch current items from the harvester
            current_devices = self._harvester.return_items()

            if not previous_devices:
                self.logger.info(
                    f"First run, treating all {len(current_devices)} items as new"
                )
                operations = [
                    Operation(type=OperationType.ADD, device_id=item.id, device=item)
                    for item in current_devices
                ]
                return Items(
                    devices=current_devices,
                    operations=operations,
                    state={"previous_devices": current_devices},
                )

            previous_devices = [
                Device.model_validate(device) for device in previous_devices
            ]

            self.logger.debug(
                """Comparing current state (%s devices)
                with previous state (%s devices)""",
                len(current_devices),
                len(previous_devices),
            )

            operations = self._detect_operations(previous_devices, current_devices)

            self.logger.info("Detected %s changes: ", len(operations))
            self.logger.debug("Object IDs: %s", [op.device_id for op in operations])

            if len(operations) == 0:
                self.logger.info(
                    "No new or updated items are discovered, stopping pipeline"
                )
                return Items(
                    devices=current_devices,
                    operations=operations,
                    stop_pipeline=True,
                )

            return Items(
                devices=current_devices,
                operations=operations,
                state={"previous_devices": current_devices},
            )

        except Exception as e:
            self.logger.error(f"Error during harvester run: {e}")
            raise HarvesterError(
                f"Failed to retrieve or process items: {str(e)}"
            ) from e

    def _detect_operations(
        self, previous: Sequence[Device], current: Sequence[Device]
    ) -> list[Operation]:
        """
        Detect changes between previous and current item sets.

        Identifies items that were added, updated, or deleted by comparing
        the two datasets using item IDs and content hashes.

        Args:
            previous: Items from the previous run
            current: Items from the current run

        Returns:
            list[Operation]: List of operations representing changes
        """
        operations = []

        # Create maps for faster lookups
        prev_map = {device.id: device for device in previous}
        curr_map = {device.id: device for device in current}

        # Create content hashes for more efficient comparisons
        prev_hashes = {
            device_id: self._hash_content(device.model_dump())
            for device_id, device in prev_map.items()
        }

        # Find additions and updates
        for device_id, device in curr_map.items():
            if device_id not in prev_map:
                # Item is new
                operations.append(
                    Operation(
                        type=OperationType.ADD, device_id=device_id, device=device
                    )
                )
            elif self._is_item_changed(
                prev_map[device_id], device, prev_hashes.get(device_id)
            ):
                # Item exists but was updated
                operations.append(
                    Operation(
                        type=OperationType.UPDATE, device_id=device_id, device=device
                    )
                )

        # Find deletions
        for device_id, device in prev_map.items():
            if device_id not in curr_map:
                operations.append(
                    Operation(
                        type=OperationType.DELETE, device_id=device_id, device=device
                    )
                )

        return operations

    def _is_item_changed(
        self, prev_device: Device, curr_device: Device, prev_hash: str | None = None
    ) -> bool:
        """
        Determine if an device has changed by comparing content.

        This method uses content hashing for more efficient comparisons when available.

        Args:
            prev_device: Device from previous run
            curr_device: Corresponding device from current run
            prev_hash: Optional pre-computed hash of previous device content

        Returns:
            bool: True if the device's content has changed, False otherwise
        """
        # If we have a pre-computed hash, use it for comparison
        if prev_hash is not None:
            curr_hash = self._hash_content(curr_device.model_dump())
            return prev_hash != curr_hash

        # Fall back to direct content comparison if no hash provided
        return prev_device.model_dump() != curr_device.model_dump()

    def _hash_content(self, content: dict) -> str:
        """
        Create a hash of item content for efficient change detection.

        Args:
            content: The content to hash

        Returns:
            str: Hash string representing the content
        """
        try:
            # For dictionary or complex content
            if isinstance(content, dict):
                # Sort keys for consistent hashing
                content_str = json.dumps(content, sort_keys=True)
            else:
                content_str = str(content)

            return hashlib.md5(content_str.encode("utf-8")).hexdigest()
        except Exception:
            # If hashing fails, fall back to string representation
            return str(content)
