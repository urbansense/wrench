# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

import logging
from typing import Any, Literal

from pydantic import BaseModel, PrivateAttr

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
    CatalogerConfig,
    ComponentConfig,
    GrouperConfig,
    HarvesterConfig,
    MetadataEnricherConfig,
)
from .types import PipelineType

logger = logging.getLogger(__name__)


class PipelineConfig(BaseModel):
    """
    Configuration class for pipelines.

    For template pipelines, subclass this and override _get_components
    and _get_connections.
    """

    harvester_config: dict[str, Any] | None = None
    grouper_config: dict[str, Any] | None = None
    metadataenricher_config: dict[str, Any] | None = None
    cataloger_config: dict[str, Any] | None = None

    # For raw pipeline configs (non-template)
    component_config: dict[str, ComponentConfig] = {}
    connection_config: list[ConnectionDefinition] = []
    template_: Literal[PipelineType.NONE] = PipelineType.NONE

    _harvester: BaseHarvester | None = PrivateAttr(default=None)
    _grouper: BaseGrouper | None = PrivateAttr(default=None)
    _metadataenricher: BaseMetadataEnricher | None = PrivateAttr(default=None)
    _cataloger: BaseCataloger | None = PrivateAttr(default=None)

    def _parse_components(self) -> None:
        """Parse all component configs into instances."""
        if self.harvester_config:
            self._harvester = HarvesterConfig(root=self.harvester_config).parse()
        if self.grouper_config:
            self._grouper = GrouperConfig(root=self.grouper_config).parse()
        if self.metadataenricher_config:
            self._metadataenricher = MetadataEnricherConfig(
                root=self.metadataenricher_config
            ).parse()
        if self.cataloger_config:
            self._cataloger = CatalogerConfig(root=self.cataloger_config).parse()

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
        self._parse_components()
        return PipelineDefinition(
            components=self._get_components(),
            connections=self._get_connections(),
        )

    def get_harvester(self) -> BaseHarvester:
        if self._harvester is None:
            raise ValueError("No harvester configured")
        return self._harvester

    def get_grouper(self) -> BaseGrouper:
        if self._grouper is None:
            raise ValueError("No grouper configured")
        return self._grouper

    def get_metadataenricher(self) -> BaseMetadataEnricher:
        if self._metadataenricher is None:
            raise ValueError("No metadata enricher configured")
        return self._metadataenricher

    def get_cataloger(self) -> BaseCataloger:
        if self._cataloger is None:
            raise ValueError("No cataloger configured")
        return self._cataloger
