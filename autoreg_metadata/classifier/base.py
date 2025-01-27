from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class ClassificationResult(BaseModel, Generic[T]):
    attribute: str = Field(
        description="Attribute by which the input is classified, examples may be 'size', 'color', 'type' "
    )
    classification_result: dict[str, list[T]]
    # optional only for hierarchical classification
    parent_classes: dict[str, set[str]] = {}


class BaseClassifier(ABC):

    @abstractmethod
    def predict(self, text: str, **kwargs) -> set[str]:
        """
        Predict classes for the given list of texts. Must be implemented by subclasses.

        Args:
            text (str): The text to classify
            **kwargs: Additional optional arguments that may be needed by specific implementations

        Returns:
            Set[str]: A set of predicted class labels
        """
        pass

    @abstractmethod
    def classify_documents(self, documents: Any) -> ClassificationResult:
        """
        Return a dictionary where the keys are strings representing categories
        and the values are lists of items belonging to those categories.
        Returns:
            dict[str, list]: A dictionary with category names as keys and lists of items as values.
        """

        pass
