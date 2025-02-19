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
        Return a dictionary where the keys are strings representing categories
        and the values are lists of items belonging to those categories.

        Returns:
            dict[str, list]: A dictionary with category names as keys and lists of items as values.
        """
        pass
