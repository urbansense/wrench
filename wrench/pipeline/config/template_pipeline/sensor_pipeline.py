# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

from typing import Any, ClassVar, Literal

from wrench.components.cataloger import Cataloger
from wrench.components.grouper import Grouper
from wrench.components.harvester import Harvester
from wrench.components.metadataenricher import MetadataEnricher
from wrench.pipeline.config.pipeline_config import PipelineConfig
from wrench.pipeline.config.types import PipelineType
from wrench.pipeline.types import ComponentDefinition, ConnectionDefinition


class SensorPipelineConfig(PipelineConfig):
    """Template configuration for sensor registration pipeline."""

    COMPONENTS: ClassVar[list[str]] = [
        "harvester",
        "grouper",
        "metadataenricher",
        "cataloger",
    ]

    template_: Literal[PipelineType.SENSOR_PIPELINE] = PipelineType.SENSOR_PIPELINE

    def _get_components(self) -> list[ComponentDefinition]:
        """Get all component definitions for the pipeline."""
        return [
            ComponentDefinition(
                name="harvester",
                component=Harvester(harvester=self.get_harvester()),
                run_params={},
            ),
            ComponentDefinition(
                name="grouper",
                component=Grouper(grouper=self.get_grouper()),
                run_params={},
            ),
            ComponentDefinition(
                name="metadataenricher",
                component=MetadataEnricher(
                    metadataenricher=self.get_metadataenricher()
                ),
                run_params={},
            ),
            ComponentDefinition(
                name="cataloger",
                component=Cataloger(cataloger=self.get_cataloger()),
                run_params={},
            ),
        ]

    def _get_connections(self) -> list[ConnectionDefinition]:
        return [
            ConnectionDefinition(
                start="harvester",
                end="grouper",
                input_config={
                    "devices": "harvester.devices",
                    "operations": "harvester.operations",
                },
            ),
            ConnectionDefinition(
                start="harvester",
                end="metadataenricher",
                input_config={
                    "devices": "harvester.devices",
                    "operations": "harvester.operations",
                },
            ),
            ConnectionDefinition(
                start="grouper",
                end="metadataenricher",
                input_config={"groups": "grouper.groups"},
            ),
            ConnectionDefinition(
                start="metadataenricher",
                end="cataloger",
                input_config={
                    "service_metadata": "metadataenricher.service_metadata",
                    "group_metadata": "metadataenricher.group_metadata",
                },
            ),
        ]

    def get_run_params(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return {}
