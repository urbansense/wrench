from abc import ABC, abstractmethod
from typing import Sequence

from pydantic import BaseModel

from wrench.models import Group


class BaseGrouper(ABC):
    @abstractmethod
    def group_items(self, items: Sequence[BaseModel]) -> list[Group]:
        """
        Groups the given list of items into a list of Group objects.

        Args:
            items (list): A list of items to be grouped.

        Returns:
            list[Group]: A list of Group objects created from the given items.
        """
        pass
