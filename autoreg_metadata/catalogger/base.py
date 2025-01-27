from abc import ABC, abstractmethod

from autoreg_metadata.classifier.base import ClassificationResult
from autoreg_metadata.common.models import CommonMetadata


class BaseCatalogger(ABC):
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key

    @abstractmethod
    def register(self, metadata: CommonMetadata, data: ClassificationResult):
        pass
