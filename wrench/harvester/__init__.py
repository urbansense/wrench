from .base import BaseHarvester
from .sensorthings import (
    PaginationConfig,
    SensorThingsHarvester,
)

HARVESTERS: dict[str, type[BaseHarvester]] = {
    "sensorthings": SensorThingsHarvester,
}

__all__ = [
    "BaseHarvester",
    "SensorThingsHarvester",
    "PaginationConfig",
    "HARVESTERS",
]
