from abc import ABC, abstractmethod

from wrench.grouper.teleclass.core.models import (
    Document,
    EnrichedClass,
    EnrichmentResult,
)


class Enricher(ABC):
    @abstractmethod
    def enrich(
        self, enriched_classes: list[EnrichedClass], collection: list[Document]
    ) -> EnrichmentResult:
        pass
