from .base import BaseCataloger
from .noop import NoopCataloger
from .sddi import SDDICataloger

CATALOGERS: dict[str, type[BaseCataloger]] = {
    "noop": NoopCataloger,
    "sddi": SDDICataloger,
}

__all__ = [
    "BaseCataloger",
    "NoopCataloger",
    "SDDICataloger",
    "CATALOGERS",
]
