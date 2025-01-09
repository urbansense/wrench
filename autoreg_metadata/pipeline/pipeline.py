import logging

from autoreg_metadata.harvester.base import BaseHarvester

from .models import EnrichedMetadata


class Pipeline:
    def __init__(self, harvester: BaseHarvester):
        self.harvester = harvester
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enriched_metadata = EnrichedMetadata()

    # def run(self):
    #     try:
    #         sensor_data = self.harvester.fetch(10)
    #         if not sensor_data:
    #             return

    #     except Exception as e:
    #         self.logger.error("Pipeline execution failed: %s", e)
