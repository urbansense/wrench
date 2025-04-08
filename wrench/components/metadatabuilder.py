from typing import Any, Sequence

from pydantic import validate_call

from wrench.components.types import Metadata
from wrench.metadatabuilder import BaseMetadataBuilder
from wrench.models import Group, Item
from wrench.pipeline.types import Component, Operation


class MetadataBuilder(Component):
    """
    Component for creating metadata builder component from any metadata builder.

    Args:
        metadatabuilder (BaseMetadataBuilder): The metadata builder to use in the
            pipeline.
    """

    def __init__(self, metadatabuilder: BaseMetadataBuilder):
        self._metadatabuilder = metadatabuilder

    @validate_call
    async def run(
        self,
        devices: Sequence[Item],
        operations: Sequence[Operation],
        groups: Sequence[Group],
        state: dict[str, Any] = {},
    ) -> Metadata:
        """Run the metadata builder."""
        if not operations:
            return Metadata(service_metadata=None, group_metadata=[])

        service_metadata = self._metadatabuilder.build_service_metadata(devices)

        group_metadata = [
            self._metadatabuilder.build_group_metadata(group) for group in groups
        ]

        return Metadata(
            service_metadata=service_metadata, group_metadata=group_metadata
        )
