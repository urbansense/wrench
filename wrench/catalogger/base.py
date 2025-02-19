from abc import ABC, abstractmethod

from wrench.log import logger
from wrench.models import CatalogEntry


class BaseCatalogger(ABC):
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key

        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def register(self, service: CatalogEntry, groups: list[CatalogEntry]):
        pass
