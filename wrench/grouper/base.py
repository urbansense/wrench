from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class Group(BaseModel):
    name: str = Field(description="Name of the group")
    items: list[str] = Field(description="List of items belonging to this group")
    # optional only for hierarchical classification
    parent_classes: set[str] = Field(
        default=set(), description="Set of parent classes of this group"
    )


class BaseGrouper(ABC):
    @abstractmethod
    def group_items(self, items: list) -> list[Group]:
        """
        Groups the given list of items into a list of Group objects.

        Args:
            items (list): A list of items to be grouped.

        Returns:
            list[Group]: A list of Group objects created from the given items.
        """
        pass
