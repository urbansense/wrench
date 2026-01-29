from .base import BaseGrouper
from .bertopic import BERTopicGrouper
from .kinetic import KINETIC
from .lda import LDAGrouper

GROUPERS: dict[str, type[BaseGrouper]] = {
    "kinetic": KINETIC,
    "lda": LDAGrouper,
    "bertopic": BERTopicGrouper,
}

__all__ = [
    "BaseGrouper",
    "BERTopicGrouper",
    "KINETIC",
    "LDAGrouper",
    "GROUPERS",
]
