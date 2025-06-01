from abc import ABC, abstractmethod
from typing import Sequence

from wrench.models import Device, Group


class BaseGrouper(ABC):
    @abstractmethod
    def group_items(self, devices: Sequence[Device]) -> list[Group]:
        """
        Groups the given list of items into a list of Group objects.

        Args:
            devices (list): A list of devices to be grouped.

        Returns:
            list[Group]: A list of Group objects created from the given items.
        """
        pass

    def process_operations(self, existing_groups: Sequence[Group], operations):
        pass
