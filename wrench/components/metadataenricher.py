from typing import Any

from pydantic import validate_call

from wrench.components.types import Metadata
from wrench.log import logger
from wrench.metadataenricher import BaseMetadataEnricher
from wrench.models import Device, Group
from wrench.pipeline.types import Component, Operation
from wrench.utils.performance import MemoryMonitor, log_performance_metrics


class MetadataEnricher(Component):
    """
    Component for creating metadata builder component from any metadata builder.

    Args:
        metadataenricher (BaseMetadataEnricher): The metadata builder to use in the
            pipeline.
    """

    def __init__(self, metadataenricher: BaseMetadataEnricher):
        self._metadataenricher = metadataenricher
        self.logger = logger.getChild(self.__class__.__name__)

    @validate_call
    async def run(
        self,
        devices: list[Device],
        operations: list[Operation],
        groups: list[Group],
        state: dict[str, Any] | None = None,
    ) -> Metadata:
        """Run the metadata builder."""
        state = state or {}
        monitor = MemoryMonitor()
        prev_group_metadata: dict = state.get("prev_group_metadata")

        with monitor.track_component("MetadataEnricher") as metrics:
            # always rebuild service_metadata
            service_metadata = self._metadataenricher.build_service_metadata(devices)

            if not prev_group_metadata:
                # First run - build all group metadata
                group_metadata = [
                    self._metadataenricher.build_group_metadata(group)
                    for group in groups
                ]

                result = Metadata(
                    service_metadata=service_metadata,
                    group_metadata=group_metadata,
                    state={
                        "prev_group_metadata": {
                            group.name: [meta.title, meta.description]
                            for group, meta in zip(groups, group_metadata)
                        }
                    },
                )

            elif not operations:
                # No operations - return empty result but preserve state
                result = Metadata(
                    service_metadata=None,
                    group_metadata=[],
                    state={
                        "prev_group_metadata": prev_group_metadata,
                    },
                )

            else:
                # Incremental update - process only affected groups
                group_metadata = []
                for group in groups:
                    if group.name not in prev_group_metadata:
                        # New group
                        group_metadata.append(
                            self._metadataenricher.build_group_metadata(group)
                        )
                    else:
                        # Existing group - reuse previous metadata
                        metadata_title = prev_group_metadata[group.name][0]
                        metadata_description = prev_group_metadata[group.name][1]
                        group_metadata.append(
                            self._metadataenricher.build_group_metadata(
                                group, metadata_title, metadata_description
                            )
                        )

                result = Metadata(
                    service_metadata=service_metadata,
                    group_metadata=group_metadata,
                    state={
                        "prev_group_metadata": {
                            group.name: [meta.title, meta.description]
                            for group, meta in zip(groups, group_metadata)
                        }
                    },
                )

        log_performance_metrics(metrics, self.logger)
        result._performance_metrics = metrics
        return result
