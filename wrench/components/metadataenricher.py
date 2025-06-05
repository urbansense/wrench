from typing import Any, Sequence

from pydantic import validate_call

from wrench.components.types import Metadata
from wrench.metadataenricher import BaseMetadataEnricher
from wrench.models import Device, Group
from wrench.pipeline.types import Component, Operation


class MetadataEnricher(Component):
    """
    Component for creating metadata builder component from any metadata builder.

    Args:
        metadataenricher (BaseMetadataEnricher): The metadata builder to use in the
            pipeline.
    """

    def __init__(self, metadataenricher: BaseMetadataEnricher):
        self._metadataenricher = metadataenricher

    @validate_call
    async def run(
        self,
        devices: Sequence[Device],
        operations: Sequence[Operation],
        groups: Sequence[Group],
        state: dict[str, Any] = {},
    ) -> Metadata:
        """Run the metadata builder."""
        prev_group_metadata: dict = state.get("prev_group_metadata")
        # always rebuild service_metadata
        service_metadata = self._metadataenricher.build_service_metadata(devices)

        if not prev_group_metadata:
            group_metadata = [
                self._metadataenricher.build_group_metadata(group) for group in groups
            ]

            metadata = Metadata(
                service_metadata=service_metadata,
                group_metadata=group_metadata,
                state={
                    "prev_group_metadata": {
                        group.name: [meta.title, meta.description]
                        for group, meta in zip(groups, group_metadata)
                    }
                },
            )

            return metadata

        if not operations:
            return Metadata(
                service_metadata=None,
                group_metadata=[],
                state={
                    "prev_group_metadata": prev_group_metadata,
                },
            )

        group_metadata = []
        for group in groups:
            if group.name not in prev_group_metadata:
                group_metadata.append(
                    self._metadataenricher.build_group_metadata(group)
                )
            else:
                metadata_title = prev_group_metadata[group.name][0]
                metadata_description = prev_group_metadata[group.name][1]
                group_metadata.append(
                    self._metadataenricher.build_group_metadata(
                        group, metadata_title, metadata_description
                    )
                )

        return Metadata(
            service_metadata=service_metadata,
            group_metadata=group_metadata,
            state={
                "prev_group_metadata": {
                    group.name: [meta.title, meta.description]
                    for group, meta in zip(groups, group_metadata)
                }
            },
        )
