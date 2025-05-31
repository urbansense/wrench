from abc import ABC, abstractmethod

from wrench.models import Device, Group


class BaseGrouper(ABC):
    @abstractmethod
    def group_items(self, devices: list[Device]) -> list[Group]:
        """
        Groups the given list of items into a list of Group objects.

        Args:
            devices (list): A list of devices to be grouped.

        Returns:
            list[Group]: A list of Group objects created from the given items.
        """
        pass

    def process_operations(
        self,
        existing_groups: list[Group],
        new_devices: list[Device],
        updated_devices: list[Device],
        deleted_devices: list[Device],
    ) -> tuple[list[Group], list[Group]]:
        # Set to track which groups were affected
        affected_group_names = set()

        if new_devices or updated_devices:
            # Create new groups from added and updated items
            new_groups = self.group_items(new_devices + updated_devices)
            # Track which groups were affected
            affected_group_names.update(group.name for group in new_groups)
            # Merge new groups into existing groups
            self._merge_groups(existing_groups, new_groups)

        if deleted_devices:
            # Get names of groups affected by deletions
            deleted_from_groups = self._remove_items(existing_groups, deleted_devices)
            affected_group_names.update(deleted_from_groups)

        # Create list of affected groups (only return groups that still exist)
        affected_groups = [
            group for group in existing_groups if group.name in affected_group_names
        ]

        return existing_groups, affected_groups

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
