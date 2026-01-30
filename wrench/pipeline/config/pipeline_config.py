# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict

from wrench.cataloger import BaseCataloger
from wrench.grouper import BaseGrouper
from wrench.harvester import BaseHarvester
from wrench.metadataenricher import BaseMetadataEnricher
from wrench.pipeline.types import (
    ComponentDefinition,
    ConnectionDefinition,
    PipelineDefinition,
)

from .object_config import (
    Cataloger,
    ComponentConfig,
    Grouper,
    Harvester,
    MetadataEnricher,
)
from .types import PipelineType

logger = logging.getLogger(__name__)


class PipelineConfig(BaseModel):
    """
    Configuration class for pipelines.

    For template pipelines, subclass this and override _get_components
    and _get_connections.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    harvester: Harvester | None = None
    grouper: Grouper | None = None
    metadataenricher: MetadataEnricher | None = None
    cataloger: Cataloger | None = None

    # For raw pipeline configs (non-template)
    component_config: dict[str, ComponentConfig] = {}
    connection_config: list[ConnectionDefinition] = []
    template_: Literal[PipelineType.NONE] = PipelineType.NONE

    def _get_components(self) -> list[ComponentDefinition]:
        """Get component definitions. Override in subclasses for template pipelines."""
        return [
            ComponentDefinition(
                name=name,
                component=config.parse(),
                run_params=config.get_run_params(),
            )
            for name, config in self.component_config.items()
        ]

    def _get_connections(self) -> list[ConnectionDefinition]:
        """Get connection definitions. Override in subclasses for template pipelines."""
        return self.connection_config

    def parse(self) -> PipelineDefinition:
        """Parse the config and return a PipelineDefinition."""
        return PipelineDefinition(
            components=self._get_components(),
            connections=self._get_connections(),
        )

    def get_harvester(self) -> BaseHarvester:
        if self.harvester is None:
            raise ValueError("No harvester configured")
        return self.harvester

    def get_grouper(self) -> BaseGrouper:
        if self.grouper is None:
            raise ValueError("No grouper configured")
        return self.grouper

    def get_metadataenricher(self) -> BaseMetadataEnricher:
        if self.metadataenricher is None:
            raise ValueError("No metadata enricher configured")
        return self.metadataenricher

    def get_cataloger(self) -> BaseCataloger:
        if self.cataloger is None:
            raise ValueError("No cataloger configured")
        return self.cataloger
