import logging
from harvester.base import Harvester
from models import EnrichedMetadata


class Pipeline:
    def __init__(self, harvester: Harvester, classifier: Classifier, catalogger: Catalogger):
        self.harvester = harvester
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enriched_metadata = EnrichedMetadata()

    def run(self):
        try:
            sensor_data = self.harvester.fetch(10)
            if not sensor_data:
                return

        except Exception as e:
            self.logger.error("Pipeline execution failed: %s", e)
