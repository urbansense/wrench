from .base import BaseMetadataEnricher
from .sensorthings import SensorThingsMetadataEnricher

METADATA_ENRICHERS: dict[str, type[BaseMetadataEnricher]] = {
    "sensorthings": SensorThingsMetadataEnricher,
}

__all__ = [
    "BaseMetadataEnricher",
    "SensorThingsMetadataEnricher",
    "METADATA_ENRICHERS",
]
