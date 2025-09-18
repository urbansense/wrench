# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

from typing import ClassVar, Literal

from wrench.components.cataloger import Cataloger
from wrench.components.grouper import Grouper
from wrench.components.harvester import Harvester
from wrench.components.metadataenricher import MetadataEnricher
from wrench.pipeline.config.object_config import ComponentType
from wrench.pipeline.config.template_pipeline.base import TemplatePipelineConfig
from wrench.pipeline.config.types import PipelineType
from wrench.pipeline.types import ConnectionDefinition


class SensorRegistrationPipelineConfig(TemplatePipelineConfig):
    """Template configuration for sensor registration pipeline."""

    COMPONENTS: ClassVar[list[str]] = [
        "harvester",
        "grouper",
        "metadataenricher",
        "cataloger",
    ]

    harvester: ComponentType | None = None
    grouper: ComponentType | None = None
    metadataenricher: ComponentType | None = None
    cataloger: ComponentType | None = None

    template_: Literal[PipelineType.SENSOR_PIPELINE] = PipelineType.SENSOR_PIPELINE

    def _get_harvester(self) -> Harvester:
        return Harvester(harvester=self.get_default_harvester())

    def _get_grouper(self) -> Grouper:
        return Grouper(grouper=self.get_default_grouper())

    def _get_metadataenricher(self) -> MetadataEnricher:
        return MetadataEnricher(metadataenricher=self.get_default_metadataenricher())

    def _get_cataloger(self) -> Cataloger:
        return Cataloger(cataloger=self.get_default_cataloger())

    def _get_connections(self) -> list[ConnectionDefinition]:
        connections = []
        connections.append(
            ConnectionDefinition(
                start="harvester",
                end="grouper",
                input_config={
                    "devices": "harvester.devices",
                    "operations": "harvester.operations",
                },
            )
        )
        connections.append(
            ConnectionDefinition(
                start="harvester",
                end="metadataenricher",
                input_config={
                    "devices": "harvester.devices",
                    "operations": "harvester.operations",
                },
            )
        )
        connections.append(
            ConnectionDefinition(
                start="grouper",
                end="metadataenricher",
                input_config={"groups": "grouper.groups"},
            )
        )
        connections.append(
            ConnectionDefinition(
                start="metadataenricher",
                end="cataloger",
                input_config={
                    "service_metadata": "metadataenricher.service_metadata",
                    "group_metadata": "metadataenricher.group_metadata",
                },
            )
        )
        return connections
