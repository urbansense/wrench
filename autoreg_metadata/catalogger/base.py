from abc import ABC, abstractmethod

from pydantic import BaseModel

from autoreg_metadata.common.models import CommonMetadata
from autoreg_metadata.grouper.base import Group


class CatalogEntry(BaseModel):
    name: str
    description: str


class BaseCatalogger(ABC):
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key

    @abstractmethod
    def register(self, metadata: CommonMetadata, data: list[Group]):
        pass
