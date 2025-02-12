from abc import ABC, abstractmethod

from autoreg_metadata.common.models import CommonMetadata
from autoreg_metadata.grouper.base import Group


class BaseCatalogger(ABC):
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key

    @abstractmethod
    def register(self, metadata: CommonMetadata, data: Group):
        pass
