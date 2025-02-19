from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from wrench.models import CommonMetadata, Item

T = TypeVar("T", bound=BaseModel)  # For input
T_co = TypeVar("T_co", bound=BaseModel, covariant=True)  # For output


class BaseHarvester(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url

    @abstractmethod
    def get_metadata(self) -> CommonMetadata:
        pass

    @abstractmethod
    def get_items(self) -> list[Item]:
        pass


class TranslationService(ABC, Generic[T]):
    url: str

    @abstractmethod
    def translate[T: BaseModel](obj: T) -> T:
        pass