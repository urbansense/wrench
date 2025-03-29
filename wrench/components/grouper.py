import copy
from typing import Sequence

from pydantic import validate_call

from wrench.components.types import Groups
from wrench.grouper import BaseGrouper
from wrench.models import Group, Item
from wrench.pipeline.component import Component
from wrench.pipeline.types import Operation, OperationType


class Grouper(Component):
    """
    Component for creating grouper component from any grouper.

    Args:
        grouper (BaseGrouper): The grouper to use in the pipeline.
    """

    def __init__(self, grouper: BaseGrouper):
        self._grouper = grouper

    @validate_call()
    async def run(self, devices: Sequence[Item]) -> Groups:
        """Run the grouper and group Items."""
        groups = self._grouper.group_items(devices)
        return Groups(groups=groups)


class IncrementalGrouper(Component):
    """Grouper that handles operations on Groups."""

    def __init__(self, grouper: BaseGrouper):
        self._grouper = grouper
        self._groups = None

    @validate_call(config={"extra": "allow"})
    async def run(
        self, devices: Sequence[Item], operations: Sequence[Operation]
    ) -> Groups:
        # Case 1: Incremental update - apply operations to existing groups
        if self._groups and operations:
            # Get both the full updated list and just the modified groups
            updated_groups, modified_groups = self._apply_operations(
                self._groups, operations
            )
            # Store the complete group list internally
            self._groups = updated_groups
            # Return only the modified groups
            return Groups(groups=modified_groups)

        # Case 2: No operations - return empty list
        if self._groups and not operations:
            return Groups(groups=[])

        # Case 2: First run or full rebuild - process all devices
        # Update internal state and return all groups
        self._groups = self._grouper.group_items(devices)
        return Groups(groups=self._groups)

    def _apply_operations(
        self, groups: list[Group], operations: list[Operation]
    ) -> tuple[list[Group], list[Group]]:
        """
        Apply operations to update groups.

        Args:
            groups (list[Group]): List of existing groups to be updated.
            operations (list[Operation]): List of operations to be performed.

        Returns:
            list[Group]: List of the final updated groups.
            list[Group]: List; of only modified groups.
        """
        # Make a deep copy to avoid modifying the stored state directly
        updated_groups = copy.deepcopy(groups)
        added_items: list[Item] = []
        updated_items: list[Item] = []
        deleted_items: list[Item] = []

        for op in operations:
            if op.type == OperationType.ADD:
                added_items.append(op.item)
            elif op.type == OperationType.UPDATE:
                updated_items.append(op.item)
            elif op.type == OperationType.DELETE:
                deleted_items.append(op.item)

        modified_groups = self._process_groups(
            updated_groups, added_items, updated_items, deleted_items
        )

        return updated_groups, modified_groups

    def _process_groups(
        self,
        updated_groups: list[Group],
        added_items: list[Item],
        updated_items: list[Item],
        deleted_items: list[Item],
    ) -> list[Group]:
        """
        Process groups by merging new groups with existing groups.

        Args:
            updated_groups: The current list of groups
            added_items: Items that were added
            updated_items: Items that were updated
            deleted_items: Items that were deleted
        """
        modified_groups = []
        # Merge new groups with existing groups if there are new items
        # Adds these to updated_groups if there are new items
        if added_items or updated_items:
            # Generate new groups from added and updated items
            modified_groups.append(
                *self._grouper.group_items([*added_items, *updated_items])
            )
            self._merge_groups(updated_groups, modified_groups)

        # Delete items from existing groups if there are deleted items
        if deleted_items:
            modified_groups.append(*self._delete_items(updated_groups, deleted_items))

        return modified_groups

    def _merge_groups(self, existing_groups: list[Group], new_groups: list[Group]):
        """
        Merge new groups into existing groups.

        Items in new groups will replace existing items with the same ID,
        and new items will be added to existing groups.
        New groups that don't exist in existing_groups will be added.

        Args:
            existing_groups (list[Group]): List of existing Group objects
            new_groups (list[Group]): List of new Group objects to merge in
        """
        # Create a mapping of existing groups by name for faster lookup
        existing_groups_by_name = {group.name: group for group in existing_groups}

        for new_group in new_groups:
            if new_group.name in existing_groups_by_name:
                # Group exists, merge items
                existing_group = existing_groups_by_name[new_group.name]

                # Create a mapping of existing items by ID
                existing_items_by_id = {item.id: item for item in existing_group.items}

                # Update existing items and add new ones
                for new_item in new_group.items:
                    item_id = new_item.id
                    if item_id in existing_items_by_id:
                        # Replace existing item
                        idx = existing_group.items.index(existing_items_by_id[item_id])
                        existing_group.items[idx] = new_item
                    else:
                        # Add new item
                        existing_group.items.append(new_item)

                # Update parent_classes if they exist in the model
                if hasattr(new_group, "parent_classes") and hasattr(
                    existing_group, "parent_classes"
                ):
                    existing_group.parent_classes.update(new_group.parent_classes)

            else:
                # Group doesn't exist, add it
                existing_groups.append(new_group)

    def _delete_items(
        self, existing_groups: list[Group], deleted_items: list[Item]
    ) -> list[Group]:
        """
        Deletes provided items from existing group.

        Args:
            existing_groups (list[Group]): List of existing Group objects.
            deleted_items (list[Item]): List of items to be deleted.

        Returns:
            list[Group]: List of modified groups as a result of deleting its items.
        """
        modified_groups: list[Group] = []

        for group in existing_groups:
            for item in deleted_items:
                if item in group.items:
                    group.items.remove(item)
                    modified_groups.append(group)

        return modified_groups
