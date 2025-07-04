from abc import ABC, abstractmethod

from wrench.log import logger
from wrench.models import Device


class BaseHarvester(ABC):
    def __init__(self):
        """Initializes logger for all harvester classes."""
        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def return_devices(self) -> list[Device]:
        pass
