from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Define a generic type for source-specific data
T = TypeVar("T")


class TimeFrame(BaseModel):
    start_time: datetime
    latest_time: datetime


class Item(BaseModel):
    id: str


class CommonMetadata(BaseModel, Generic[T]):
    """
    Extensible common metadata format that preserves source-specific information
    while providing standardized fields for common attributes
    """

    # required fields
    identifier: str
    title: str
    description: str
    endpoint_url: str

    # standard, but optional fields
    spatial_extent: str | None = ""
    temporal_extent: TimeFrame | None = None
    tags: list[str] = []
    keywords: list[str] = []

    # data quality and provenance
    source_type: str
    last_updated: datetime | None = None
    update_frequency: str | None = None
    owner: str | None = None

    # license and access information
    license: str | None = None

    # extensibility mechanisms
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    source_specific_data: T | None = None

    model_config = {"extra": "allow"}

    def add_custom_attribute(self, key: str, value: Any):
        """Add a custom attribute to the metadata"""
        self.custom_attributes[key] = value

    def get_custom_attribute(self, key: str, default: Any = None) -> Any:
        """Retrieve a custom attribute"""
        return self.custom_attributes.get(key, default)
