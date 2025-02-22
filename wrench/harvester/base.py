from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from wrench.models import CommonMetadata, Item

T = TypeVar("T", bound=BaseModel)  # For input
T_co = TypeVar("T_co", bound=BaseModel, covariant=True)  # For output


class BaseHarvester(ABC):
    def __init__(self, base_url: str):
        """
        Initializes the harvester with the given base URL.

        Args:
            base_url (str): The base URL for the harvester.
        """
        self.base_url = base_url

    @abstractmethod
    def get_metadata(self) -> CommonMetadata:
        """
        Retrieve metadata information.

        Returns:
            CommonMetadata: The metadata information.
        """
        pass

    @abstractmethod
    def get_items(self) -> list[Item]:
        """
        Retrieve a list of items.

        Returns:
            list[Item]: A list of items.
        """
        pass


class TranslationService(ABC, Generic[T]):
    url: str

    @abstractmethod
    def translate[T: BaseModel](self, obj: T) -> T:
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
