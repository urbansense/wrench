from typing import Sequence

from pydantic import validate_call

from wrench.components.types import Items
from wrench.harvester import BaseHarvester
from wrench.models import Item
from wrench.pipeline.types import Component, Operation, OperationType


class Harvester(Component):
    """
    Component for creating harvester component from any harvester.

    Args:
        harvester (BaseHarvester): The harvester to use in the pipeline.
    """

    def __init__(self, harvester: BaseHarvester):
        self._harvester = harvester

    @validate_call
    async def run(self) -> Items:
        """Run the harvester and extract items."""
        # Directly get items from the harvester
        devices = self._harvester.return_items()
        return Items(devices=devices)


class IncrementalHarvester(Component):
    """Harvester that determines operations by comparing with previous state."""

    def __init__(self, harvester: BaseHarvester):
        self._harvester = harvester
        self._previous_items = None  # will be stored between runs

    @validate_call
    async def run(self) -> Items:
        current_items = self._harvester.return_items()

        if self._previous_items:
            operations = self._detect_operations(self._previous_items, current_items)
        else:
            operations = [
                Operation(type=OperationType.ADD, item_id=item.id, item=item)
                for item in current_items
            ]

        self._previous_items = current_items

        return Items(devices=current_items, operations=operations)

    def _detect_operations(
        self, previous: Sequence[Item], current: Sequence[Item]
    ) -> list[Operation]:
        operations = []
        prev_map = {item.id: item for item in previous}
        curr_map = {item.id: item for item in current}

        for item_id, item in curr_map.items():
            if item_id not in prev_map:
                operations.append(
                    Operation(type=OperationType.ADD, item_id=item_id, item=item)
                )
            elif item.content != prev_map[item_id].content:
                operations.append(
                    Operation(type=OperationType.UPDATE, item_id=item_id, item=item)
                )

        for item_id, item in prev_map.items():
            if item_id not in curr_map:
                operations.append(
                    Operation(type=OperationType.DELETE, item_id=item_id, item=item)
                )

        return operations
