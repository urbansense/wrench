from .base import BaseGrouper
from .kinetic import KINETIC

GROUPERS: dict[str, type[BaseGrouper]] = {
    "kinetic": KINETIC,
}

__all__ = [
    "BaseGrouper",
    "KINETIC",
    "GROUPERS",
]
