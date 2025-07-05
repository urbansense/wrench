from datetime import datetime
from typing import Any, TypeVar

import geojson
from geojson.feature import Feature, FeatureCollection
from geojson.geometry import Geometry
from geojson.utils import coords
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Define a generic type for source-specific data
T = TypeVar("T")


class Location(BaseModel):
    encoding_type: str
    location: Feature | FeatureCollection | Geometry = Field(
        description="GeoJSON location data as Feature, FeatureCollection, or Geometry"
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("location", mode="before")
    @classmethod
    def validate_geojson(cls, v):
        """Validate that the location is proper GeoJSON."""
        if isinstance(v, (Feature, FeatureCollection, Geometry)):
            return v

        # If it's a dict, convert to a Feature object regardless of type
        if isinstance(v, dict):
            if not v.get("type"):
                raise ValueError("GeoJSON object must have a 'type' field")

            # If already a Feature, use as is, otherwise wrap it as a Feature
            if v.get("type") == "Feature":
                return geojson.GeoJSON.to_instance(v)
            elif v.get("type") in [
                "Point",
                "LineString",
                "Polygon",
                "MultiPoint",
                "MultiLineString",
                "MultiPolygon",
                "GeometryCollection",
            ]:
                # Create a Feature with this geometry
                feature_dict = {"type": "Feature", "geometry": v, "properties": {}}
                return geojson.GeoJSON.to_instance(feature_dict)

        raise ValueError("Location must be a valid GeoJSON object")

    def get_coordinates(self) -> list[tuple[float, float]]:
        """
        Retrieves the coordinates of the location.

        Returns:
            list[tuple[float, float]]: List of tuples with latitude and longitude
            of the location.
        """
        return list(coords(self.location))


class TimeFrame(BaseModel):
    start_time: datetime
    latest_time: datetime


class Device(BaseModel):
    """Device model representing an entity with an ID."""

    id: str
    name: str
    description: str
    datastreams: set[str]
    sensors: set[str]
    observed_properties: set[str]
    locations: list[Location]
    time_frame: TimeFrame | None  # if there are no datastreams

    properties: dict[str, Any] | None = None

    _raw_data: dict[str, Any]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def to_string(self, exclude: list[str] | None = None):
        data = self.model_dump(exclude=set(exclude))
        return "\n".join([str(val) for attr, val in data.items()]).strip()

    def __eq__(self, other) -> bool:
        if not isinstance(other, Device):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class CommonMetadata(BaseModel):
    """
    Extensible common metadata format.

    Attributes:
        identifier (str): A unique identifier for the metadata.
        title (str): The title of the metadata.
        description (str): A brief description of the metadata.
        endpoint_urls (list[str]): The URL endpoints where the metadata can be accessed.

        spatial_extent (str, optional): The spatial extent of the data.
                                        Defaults to an empty string.
        temporal_extent (TimeFrame, optional): The temporal extent of the data.
                                               Defaults to None.
        tags (list[str], optional): A list of tags associated with the metadata.
                                    Defaults to an empty list.
        keywords (list[str], optional): A list of keywords associated with
                                        the metadata. Defaults to an empty list.

        source_type (str): The type of source from which the data originates.
        last_updated (datetime, optional): The date and time when the metadata
                                           was last updated. Defaults to None.
        update_frequency (str, optional): The frequency at which the data is
                                          updated. Defaults to None.
        owner (str, optional): The owner of the metadata. Defaults to None.

        license (str, optional): The license under which the data is provided.
                                 Defaults to None.
    """

    # required fields
    identifier: str
    title: str
    description: str
    endpoint_urls: list[str]

    # standard, but optional fields
    spatial_extent: str = ""
    temporal_extent: TimeFrame | None = None
    tags: list[str] = []
    keywords: list[str] = []
    thematic_groups: list[str] = []

    # data quality and provenance
    source_type: str
    last_updated: datetime | None = None
    update_frequency: str | None = None
    owner: str | None = None

    license: str | None = None
    "License and access information"


class Group(BaseModel):
    """Group model representing a collection of items."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    "Name of the group"
    devices: list[Device]
    "List of items belonging to this group"
    keywords: list[str] = []
    "List of keywords associated with this group"
    # optional only for hierarchical classification
    parent_classes: set[str] = set()
    "Set of parent classes of this group,for hierarchical classification tasks."
