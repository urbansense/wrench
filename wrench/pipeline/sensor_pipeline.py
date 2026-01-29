# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

import asyncio

from pydantic import ValidationError

from wrench.cataloger import BaseCataloger
from wrench.grouper import BaseGrouper
from wrench.harvester import BaseHarvester
from wrench.log import logger
from wrench.metadataenricher import BaseMetadataEnricher
from wrench.pipeline.config import (
    PipelineRunner,
    SensorPipelineConfig,
)
from wrench.pipeline.exceptions import PipelineDefinitionError
from wrench.pipeline.pipeline_graph import PipelineResult
from wrench.scheduler.config import SchedulerConfig


class SensorRegistrationPipeline:
    """A class to simplify building sensor registration pipeline."""

    def __init__(
        self,
        harvester: BaseHarvester,
        grouper: BaseGrouper,
        metadataenricher: BaseMetadataEnricher,
        cataloger: BaseCataloger,
        scheduler_config: SchedulerConfig | None = None,
    ):
        try:
            config = SensorPipelineConfig(
                # argument type are fixed in the Config object
                harvester_config=harvester,  # type: ignore[arg-type]
                grouper_config=grouper,  # type: ignore[arg-type]
                metadataenricher_config=metadataenricher,  # type: ignore[arg-type]
                cataloger_config=cataloger,  # type: ignore[arg-type]
            )
        except (ValidationError, ValueError) as e:
            raise PipelineDefinitionError() from e

        self.runner = PipelineRunner.from_config(config)

        self.scheduler = None
        if scheduler_config:
            self.scheduler = scheduler_config.type.create_scheduler(runner=self.runner)

        self.logger = logger.getChild(self.__class__.__name__)

    async def run_async(self) -> PipelineResult:
        """
        Asynchronously runs the sensor pipeline building process.

        Returns:
            PipelineResult: The result of the pipeline execution.
        """
        if not self.scheduler:
            return await self.runner.run({})

        try:
            self.scheduler.start()
            self.logger.info("Started Scheduler")
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
