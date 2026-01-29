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
from wrench.log import logger
from wrench.pipeline.config.object_config import ComponentType
from wrench.pipeline.config.pipeline_config import PipelineConfig
from wrench.pipeline.config.types import PipelineType
from wrench.pipeline.types import ComponentDefinition, ConnectionDefinition


class SensorPipelineConfig(PipelineConfig):
    """Template configuration for sensor registration pipeline.

    This is a pre-configured pipeline template that provides default components
    and connections for sensor registration workflows.
    """

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

    def _get_component(self, component_name: str) -> ComponentDefinition | None:
        """Get a component definition by name."""
        method = getattr(self, f"_get_{component_name}")
        component = method()
        if component is None:
            return None
        method = getattr(self, f"_get_run_params_for_{component_name}", None)
        run_params = method() if method else {}
        component_definition = ComponentDefinition(
            name=component_name,
            component=component,
            run_params=run_params,
        )
        logger.debug(f"SENSOR_PIPELINE: resolved component {component_definition}")
        return component_definition

    def _get_components(self) -> list[ComponentDefinition]:
        """Get all component definitions for the pipeline."""
        components = []
        for component_name in self.COMPONENTS:
            comp = self._get_component(component_name)
            if comp is not None:
                components.append(comp)
        return components

    def get_run_params(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return {}

    def _get_harvester(self) -> Harvester:
        return Harvester(harvester=self.get_harvester())

    def _get_grouper(self) -> Grouper:
        return Grouper(grouper=self.get_grouper())

    def _get_metadataenricher(self) -> MetadataEnricher:
        return MetadataEnricher(metadataenricher=self.get_metadataenricher())

    def _get_cataloger(self) -> Cataloger:
        return Cataloger(cataloger=self.get_cataloger())

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


# Backwards compatibility alias
SensorRegistrationPipelineConfig = SensorPipelineConfig
