from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Tuple, List

from pydantic import BaseModel

from autoreg_metadata.pipeline.models import EnrichedMetadata

T = TypeVar("T", bound=BaseModel)  # For input
T_co = TypeVar("T_co", bound=BaseModel, covariant=True)  # For output


class BaseHarvester(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url

    @abstractmethod
    def enrich(self) -> Tuple[EnrichedMetadata, List[BaseModel]]:
        pass


class TranslationService(ABC, Generic[T]):
    url: str

    @abstractmethod
    def translate(obj: T) -> T:
        pass
