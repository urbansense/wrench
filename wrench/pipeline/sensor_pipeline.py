import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import ValidationError

from wrench.cataloger import BaseCataloger
from wrench.grouper import BaseGrouper
from wrench.harvester import BaseHarvester
from wrench.log import logger
from wrench.metadatabuilder import BaseMetadataBuilder
from wrench.pipeline.config import (
    PipelineRunner,
    SensorRegistrationPipelineConfig,
)
from wrench.pipeline.exceptions import PipelineDefinitionError
from wrench.pipeline.pipeline_graph import PipelineResult
from wrench.scheduler.scheduler import IntervalScheduler


class SensorRegistrationPipeline:
    """A class to simplify building sensor registration pipeline."""

    def __init__(
        self,
        harvester: BaseHarvester,
        grouper: BaseGrouper,
        metadatabuilder: BaseMetadataBuilder,
        cataloger: BaseCataloger,
        schedule: str | None = None,
    ):
        try:
            config = SensorRegistrationPipelineConfig(
                # argument type are fixed in the Config object
                harvester_config=harvester,  # type: ignore[arg-type]
                grouper_config=grouper,  # type: ignore[arg-type]
                metadatabuilder_config=metadatabuilder,  # type: ignore[arg-type]
                cataloger_config=cataloger,  # type: ignore[arg-type]
            )
        except (ValidationError, ValueError) as e:
            raise PipelineDefinitionError() from e

        self.runner = PipelineRunner.from_config(config)
        if schedule:
            self.scheduler = IntervalScheduler(
                self.runner, scheduler=AsyncIOScheduler(), interval=schedule
            )

        self.logger = logger.getChild(self.__class__.__name__)

    async def run_async(self) -> PipelineResult:
        """
        Asynchronously runs the sensor pipeline building process.

        Returns:
            PipelineResult: The result of the pipeline execution.
        """
        if not hasattr(self, "scheduler"):
            return await self.runner.run({})

        try:
            self.scheduler.start()
            self.logger.info("Started Scheduler")
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
