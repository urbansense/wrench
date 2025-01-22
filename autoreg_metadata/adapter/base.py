from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")  # Source metadata type
U = TypeVar("U")  # Target metadata type


class MetadataAdapter(ABC, Generic[T, U]):
    """
    Abstract base class for metadata adapters that convert between different metadata formats.
    Implements the adapter pattern to make incompatible metadata formats work together.
    """

    @abstractmethod
    def adapt(self, metadata: T, **kwargs: Any) -> U:
        """
        Convert metadata from source format to target format.

        Args:
            metadata: Source metadata in format T
            **kwargs: Additional arguments needed for conversion

        Returns:
            Converted metadata in format U
        """
        pass
