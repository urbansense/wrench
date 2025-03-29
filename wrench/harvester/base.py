from abc import ABC, abstractmethod

from pydantic import BaseModel

from wrench.log import logger
from wrench.models import Item


class BaseHarvester(ABC):
    def __init__(self):
        """Initializes logger for all harvester classes."""
        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def return_items(self) -> list[Item]:
        pass


class TranslationService[T: BaseModel](ABC):
    url: str

    @abstractmethod
    def translate(self, obj: T) -> T:
        """
        Translates the given object.

        This function takes an object of type T,which must be a
        subclass of BaseModel, and returns an object of the same type.

        Args:
            obj (T): The object to be translated.

        Returns:
            T: The translated object.
        """
        pass
