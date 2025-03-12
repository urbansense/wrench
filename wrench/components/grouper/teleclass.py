from pathlib import Path
from typing import List, Union

from pydantic import BaseModel, ValidationError, validate_call

from wrench.components.decorators import register_component
from wrench.components.types import Items
from wrench.grouper.base import Group
from wrench.grouper.teleclass import TELEClassConfig, TELEClassGrouper
from wrench.pipeline.models import Component, DataModel


class GrouperOutput(DataModel):
    """Output model for grouper components."""

    groups: List[Group]


class TELEClassGrouperConfig(BaseModel):
    """Configuration for TELEClass grouper."""

    config_path: str | None = None
    llm: dict | None = None
    embedding: dict | None = None
    corpus: dict | None = None
    cache: dict | None = None
    taxonomy_metadata: dict | None = None
    taxonomy: list | None = None


@register_component("grouper", "teleclass")
class TELEClassGrouperComponent(Component):
    """TELEClass grouper component for taxonomic classification."""

    def __init__(self, config: Union[dict, str, Path]):
        """
        Initialize the TELEClass grouper component.

        Args:
            config: Either a configuration dict, file path, or TELEClassConfig object
        """
        try:
            if isinstance(config, dict):
                # if a dict was passed validate it first
                teleclass_config = TELEClassConfig.model_validate(config)
                self.grouper = TELEClassGrouper(teleclass_config)
            else:
                self.grouper = TELEClassGrouper(config)
        except ValidationError as v:
            raise ValidationError(f"Config provided doesn't match TELEClassConfig: {v}")

    @validate_call
    async def run(self, items: Items) -> GrouperOutput:
        """
        Group the provided items into taxonomic groups.

        Args:
            items: List of Thing objects from the harvester

        Returns:
            GrouperOutput containing the groups
        """
        # If the original method is synchronous, we'll wrap it
        groups = self.grouper.group_items(items.devices)

        return GrouperOutput(groups=groups)
