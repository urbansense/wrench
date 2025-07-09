from typing import Any

from pydantic import validate_call

from wrench.cataloger import BaseCataloger
from wrench.models import CommonMetadata
from wrench.pipeline.types import Component, DataModel


class CatalogerStatus(DataModel):
    success: bool = False
    groups: list[str]


class Cataloger(Component):
    """
    Component for creating cataloger component from any cataloger.

    Args:
        cataloger (BaseCataloger): The cataloger to use in the pipeline.
    """

    def __init__(self, cataloger: BaseCataloger):
        self._cataloger = cataloger

    @validate_call
    async def run(
        self,
        service_metadata: CommonMetadata | None,
        group_metadata: list[CommonMetadata],
        state: dict[str, Any] = {},
    ) -> CatalogerStatus:
        """Run the cataloger and register metadata."""
        previous_registries = state.get("previous_registries")

        if service_metadata is None:
            return CatalogerStatus(success=True, groups=[])

        # Directly get items from the harvester
        current_registries = self._cataloger.register(
            service=service_metadata,
            groups=group_metadata,
            managed_entries=previous_registries,
        )
        return CatalogerStatus(
            success=True,
            groups=[group.identifier for group in group_metadata],
            state={"previous_registries": current_registries},
        )
