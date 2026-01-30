# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

from typing import Annotated, Any

from pydantic import BaseModel, Discriminator, Field, Tag

from wrench.log import logger
from wrench.pipeline.config.config_reader import ConfigReader
from wrench.pipeline.config.pipeline_config import PipelineConfig
from wrench.pipeline.config.template_pipeline.sensor_pipeline import (
    SensorPipelineConfig,
)
from wrench.pipeline.config.types import PipelineType
from wrench.pipeline.pipeline import Pipeline
from wrench.pipeline.stores import FileStore
from wrench.pipeline.types import PipelineDefinition


def _get_discriminator_value(model: Any) -> PipelineType:
    template_ = None
    if "template_" in model:
        template_ = model["template_"]
    if hasattr(model, "template_"):
        template_ = model.template_
    return PipelineType(template_) or PipelineType.NONE


class PipelineConfigWrapper(BaseModel):
    """Parses the pipeline config based on the `template_` field."""

    config: (
        Annotated[PipelineConfig, Tag(PipelineType.NONE)]
        | Annotated[SensorPipelineConfig, Tag(PipelineType.SENSOR_PIPELINE)]
    ) = Field(discriminator=Discriminator(_get_discriminator_value))

    def parse(self) -> PipelineDefinition:
        logger.debug("PIPELINE_CONFIG: start parsing config...")
        return self.config.parse()


class PipelineRunner:
    """Runner to execute pipelines from different sources."""

    def __init__(self, pipeline_definition: PipelineDefinition, config=None):
        """Initializes a pipeline runner."""
        self.pipeline = Pipeline.from_definition(pipeline_definition, FileStore())
        self.config = config

    @classmethod
    def from_config(
        cls, config: PipelineConfig | dict[str, Any], do_cleaning: bool = False
    ) -> "PipelineRunner":
        wrapper = PipelineConfigWrapper.model_validate({"config": config})
        logger.debug(
            f"Instantiating Pipeline from config type: {wrapper.config.template_}"
        )
        return cls(wrapper.parse(), config=wrapper.config)

    @classmethod
    def from_config_file(cls, file_path):
        """Create a runner from a configuration file."""
        # Read and parse config file
        data = ConfigReader().read(file_path)
        return cls.from_config(data)

    async def run(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run the pipeline."""
        return await self.pipeline.run(user_input)
