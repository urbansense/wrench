from datetime import datetime
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict

# Define a generic type for source-specific data
T = TypeVar("T")


# define a protcol for location
@runtime_checkable
class Location(Protocol):
    def get_coordinates(self):
        tuple[float, float]


class TimeFrame(BaseModel):
    start_time: datetime
    latest_time: datetime


# all items know that Items.location has a get_coordinates function
class Item(BaseModel):
    id: str

    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)


# common metadata model
class CommonMetadata(BaseModel):
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


class CatalogEntry(BaseModel):
    name: str
    description: str
