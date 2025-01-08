from typing import List, Protocol, TypeVar, Generic

from pydantic import BaseModel
from frost.translator import FrostTranslationService

from pipeline.models import EnrichedMetadata

from abc import ABC, abstractmethod

T = TypeVar("T", bound=BaseModel)  # For input
T_co = TypeVar("T_co", bound=BaseModel, covariant=True)  # For output


class BaseHarvester(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url

    @abstractmethod
    def enrich(self, em: EnrichedMetadata) -> EnrichedMetadata:
        pass


class TranslationService(ABC, Generic[T]):
    url: str

    def translate(obj: T) -> T: ...


if __name__ == "__main__":
    ts = FrostTranslationService("http://example.com", "de")
    assert isinstance(ts, TranslationService)
