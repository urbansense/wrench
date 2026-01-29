# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

import asyncio

from wrench.cataloger import BaseCataloger
from wrench.grouper import BaseGrouper
from wrench.harvester import BaseHarvester
from wrench.log import logger
from wrench.metadataenricher import BaseMetadataEnricher
from wrench.pipeline.config import PipelineRunner
from wrench.pipeline.pipeline_graph import PipelineResult
from wrench.scheduler.config import SchedulerConfig

from .config.template_pipeline.sensor_pipeline import SensorPipelineConfig


class SensorRegistrationPipeline:
    """A class to simplify building sensor registration pipeline programmatically."""

    def __init__(
        self,
        harvester: BaseHarvester,
        grouper: BaseGrouper,
        metadataenricher: BaseMetadataEnricher,
        cataloger: BaseCataloger,
        scheduler_config: SchedulerConfig | None = None,
    ):
        # Create config and set instances directly
        config = SensorPipelineConfig()
        config._harvester = harvester
        config._grouper = grouper
        config._metadataenricher = metadataenricher
        config._cataloger = cataloger

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
