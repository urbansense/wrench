import hashlib
import json
from typing import Any, Sequence

from pydantic import validate_call

from wrench.components.types import Items
from wrench.exceptions import HarvesterError
from wrench.harvester import BaseHarvester
from wrench.log import logger
from wrench.models import Item
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
        previous_items: Sequence[dict[str, Any]] = state.get("previous_items")

        try:
            # Fetch current items from the harvester
            current_items = self._harvester.return_items()

            # Generate operations based on differences from previous run
            if previous_items:
                previous_items = [Item.model_validate(item) for item in previous_items]

                self.logger.debug(
                    """Comparing current state (%s items)
                    with previous state (%s items)""",
                    len(current_items),
                    len(previous_items),
                )
                operations = self._detect_operations(previous_items, current_items)
                self.logger.info("Detected %s changes: ", len(operations))
                self.logger.debug("Object IDs: %s", [op.item_id for op in operations])
                if len(operations) == 0:
                    self.logger.info(
                        "No new or updated items are discovered, stopping pipeline"
                    )
                    return Items(
                        devices=current_items, operations=operations, stop_pipeline=True
                    )
            else:
                # First run - treat all as new additions
                self.logger.info(
                    f"First run, treating all {len(current_items)} items as new"
                )
                operations = [
                    Operation(type=OperationType.ADD, item_id=item.id, item=item)
                    for item in current_items
                ]

            return Items(
                devices=current_items,
                operations=operations,
                state={"previous_items": current_items},
            )

        except Exception as e:
            self.logger.error(f"Error during harvester run: {e}")
            raise HarvesterError(
                f"Failed to retrieve or process items: {str(e)}"
            ) from e

    def _detect_operations(
        self, previous: Sequence[Item], current: Sequence[Item]
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
        prev_map = {item.id: item for item in previous}
        curr_map = {item.id: item for item in current}

        # Create content hashes for more efficient comparisons
        prev_hashes = {
            item_id: self._hash_content(item.content)
            for item_id, item in prev_map.items()
        }

        # Find additions and updates
        for item_id, item in curr_map.items():
            if item_id not in prev_map:
                # Item is new
                operations.append(
                    Operation(type=OperationType.ADD, item_id=item_id, item=item)
                )
            elif self._is_item_changed(
                prev_map[item_id], item, prev_hashes.get(item_id)
            ):
                # Item exists but was updated
                operations.append(
                    Operation(type=OperationType.UPDATE, item_id=item_id, item=item)
                )

        # Find deletions
        for item_id, item in prev_map.items():
            if item_id not in curr_map:
                operations.append(
                    Operation(type=OperationType.DELETE, item_id=item_id, item=item)
                )

        return operations

    def _is_item_changed(
        self, prev_item: Item, curr_item: Item, prev_hash: str | None = None
    ) -> bool:
        """
        Determine if an item has changed by comparing content.

        This method uses content hashing for more efficient comparisons when available.

        Args:
            prev_item: Item from previous run
            curr_item: Corresponding item from current run
            prev_hash: Optional pre-computed hash of previous item content

        Returns:
            bool: True if the item's content has changed, False otherwise
        """
        # If we have a pre-computed hash, use it for comparison
        if prev_hash is not None:
            curr_hash = self._hash_content(curr_item.content)
            return prev_hash != curr_hash

        # Fall back to direct content comparison if no hash provided
        return prev_item.content != curr_item.content

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
