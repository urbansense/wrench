import copy
from typing import Any, Sequence

from pydantic import validate_call

from wrench.components.types import Groups
from wrench.grouper import BaseGrouper
from wrench.models import Device, Group
from wrench.pipeline.component import Component
from wrench.pipeline.types import Operation, OperationType


class Grouper(Component):
    """Grouper that handles operations on Groups."""

    def __init__(self, grouper: BaseGrouper):
        self._grouper = grouper

    @validate_call(config={"extra": "allow", "arbitrary_types_allowed": True})
    async def run(
        self,
        devices: Sequence[Device],
        operations: Sequence[Operation],
        state: dict[str, Any] = {},
    ) -> Groups:
        # Case 1: Incremental update - apply operations to existing groups
        previous_groups = state.get("previous_groups")

        if not previous_groups:
            groups = self._grouper.group_items(devices)
            return Groups(groups=groups, state={"previous_groups": groups})

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
        self, existing_groups: Sequence[Group], operations: Sequence[Operation]
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

        # Set to track which groups were affected
        affected_group_names = set()

        # Step 1: Handle additions and updates
        if devices_to_add or devices_to_update:
            # Create new groups from added and updated items
            new_groups = self._grouper.group_items(devices_to_add + devices_to_update)
            # Track which groups were affected
            affected_group_names.update(group.name for group in new_groups)
            # Merge new groups into existing groups
            self._merge_groups(all_groups, new_groups)

        # Step 2: Handle deletions
        if devices_to_delete:
            # Get names of groups affected by deletions
            deleted_from_groups = self._remove_items(all_groups, devices_to_delete)
            affected_group_names.update(deleted_from_groups)

        # Create list of affected groups (only return groups that still exist)
        affected_groups = [
            group for group in all_groups if group.name in affected_group_names
        ]

        return all_groups, affected_groups

    def _merge_groups(self, all_groups: list[Group], new_groups: list[Group]):
        """
        Merge new groups into existing groups.

        Args:
            all_groups: Complete list of all existing groups
            new_groups: New groups to merge in
        """
        for new_group in new_groups:
            if new_group not in all_groups:
                all_groups.append(new_group)
                continue

            # Update existing items and add new ones
            existing_group = next(group for group in all_groups if group == new_group)
            for i, new_device in enumerate(new_group.devices):
                if new_device in existing_group.devices:
                    # Replace existing item
                    existing_group.devices[i] = new_device
                else:
                    # Add new item
                    existing_group.devices.append(new_device)

            # Update parent_classes if they exist
            if hasattr(new_group, "parent_classes"):
                existing_group.parent_classes.update(new_group.parent_classes)

    def _remove_items(
        self, all_groups: list[Group], devices_to_delete: list[Device]
    ) -> set[str]:
        """
        Remove specified items from all groups.

        Args:
            all_groups: Complete list of all groups
            devices_to_delete: Items to be removed

        Returns:
            set: Names of groups that were modified
        """
        affected_group_names = set()

        # Create a set of IDs for faster lookup
        delete_ids = {device.id for device in devices_to_delete}

        for group in all_groups:
            # Check if any devices in this group need to be deleted
            original_count = len(group.devices)

            # Filter out devices to delete
            group.devices = [
                device for device in group.devices if device.id not in delete_ids
            ]

            # If the count changed, this group was affected
            if len(group.devices) != original_count:
                affected_group_names.add(group.name)

        return affected_group_names
