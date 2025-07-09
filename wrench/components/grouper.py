import copy
from typing import Any

from pydantic import validate_call

from wrench.components.types import Groups
from wrench.exceptions import GrouperError
from wrench.grouper import BaseGrouper
from wrench.models import Device, Group
from wrench.pipeline.component import Component
from wrench.pipeline.exceptions import ComponentExecutionError
from wrench.pipeline.types import Operation, OperationType


class Grouper(Component):
    """Grouper that handles operations on Groups."""

    def __init__(self, grouper: BaseGrouper):
        self._grouper = grouper

    @validate_call(config={"extra": "allow", "arbitrary_types_allowed": True})
    async def run(
        self,
        devices: list[Device],
        operations: list[Operation],
        state: dict[str, Any] = {},
    ) -> Groups:
        # Case 1: Incremental update - apply operations to existing groups
        previous_groups = state.get("previous_groups")

        if not previous_groups:
            try:
                groups = self._grouper.group_devices(devices)
                return Groups(groups=groups, state={"previous_groups": groups})
            except GrouperError as e:
                raise ComponentExecutionError(
                    "grouper {} failed".format(self._grouper.__class__.__name__)
                ) from e

        if not operations:
            return Groups(
                groups=[],
                state={"previous_groups": previous_groups},
                stop_pipeline=True,
            )

        previous_groups = [Group.model_validate(groups) for groups in previous_groups]

        # Apply operations and get only the affected groups
        current_groups, affected_groups = self._apply_operations(
            previous_groups, operations
        )

        # Return only the affected groups
        return Groups(groups=affected_groups, state={"previous_groups": current_groups})

    def _apply_operations(
        self, existing_groups: list[Group], operations: list[Operation]
    ) -> tuple[list[Group], list[Group]]:
        """
        Apply operations to existing groups and track which groups were affected.

        Args:
            existing_groups: The complete list of current groups
            operations: Operations to apply (add/update/delete)

        Returns:
            tuple: (all_groups, affected_groups)
                - all_groups: Complete list of all groups after operations
                - affected_groups: Only the groups that were changed
        """
        # Make a list deep copy to avoid modifying the original state
        all_groups = list(copy.deepcopy(existing_groups))

        # Sort operations by type for batch processing
        devices_to_add: list[Device] = []
        devices_to_update: list[Device] = []
        devices_to_delete: list[Device] = []

        for op in operations:
            if op.type == OperationType.ADD:
                devices_to_add.append(op.device)
            elif op.type == OperationType.UPDATE:
                devices_to_update.append(op.device)
            elif op.type == OperationType.DELETE:
                devices_to_delete.append(op.device)

        return self._grouper.process_operations(
            all_groups, devices_to_add, devices_to_update, devices_to_delete
        )
