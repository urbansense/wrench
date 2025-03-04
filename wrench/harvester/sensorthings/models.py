from typing import Any

from geojson import Feature, FeatureCollection
from geojson.geometry import Geometry
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

model_config = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    from_attributes=True,
    coerce_numbers_to_str=True,
)


class SensorThingsBase(BaseModel):
    """Base mixin for common fields for relevant SensorThings API Entities."""

    model_config = model_config
    id: str = Field(validation_alias="@iot.id", serialization_alias="@iot.id")
    name: str
    description: str
    properties: dict[str, Any] | None = None


class Sensor(SensorThingsBase):
    encoding_type: str


class ObservedProperty(SensorThingsBase):
    pass


class Datastream(SensorThingsBase):
    unit_of_measurement: dict
    observed_area: dict | None = None
    phenomenon_time: str | None = None
    result_time: str | None = None
    sensor: Sensor = Field(alias="Sensor")
    observed_property: ObservedProperty | None = Field(
        default=None, alias="ObservedProperty"
    )


class GeoPoint(BaseModel):
    """Represents a GeoJSON Point Geometry."""

    type: str = "Point"
    coordinates: tuple[float, float]  # longitude, latitude


class Location(SensorThingsBase):
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

        # If it's a dict, try to convert it to the appropriate GeoJSON object
        if isinstance(v, dict):
            geo_type = v.get("type")
            if not geo_type:
                raise ValueError("GeoJSON object must have a 'type' field")

            try:
                if geo_type == "Feature":
                    return Feature(**v)
                elif geo_type == "FeatureCollection":
                    return FeatureCollection(**v)
                elif geo_type in [
                    "Point",
                    "LineString",
                    "Polygon",
                    "MultiPoint",
                    "MultiLineString",
                    "MultiPolygon",
                    "GeometryCollection",
                ]:
                    # For geometry types, we need to use the specific class
                    # For simplicity, we'll just return the validated dict
                    # You could import specific geometry classes if needed
                    return Geometry(**v)
                else:
                    raise ValueError(f"Unknown GeoJSON type: {geo_type}")
            except Exception as e:
                raise ValueError(f"Invalid GeoJSON format: {str(e)}")

        raise ValueError("Location must be a valid GeoJSON object")

    def get_coordinates(self) -> tuple[float, float]:
        """
        Retrieves the coordinates of the location.

        Returns:
            tuple[float, float]: Tuple with latitude and longitude
            of the location.
        """
        if isinstance(self.location, Feature):
            # Get coordinates from Feature geometry
            geometry = self.location.geometry
            if geometry and geometry.type == "Point":
                return tuple(geometry.coordinates)
        elif isinstance(self.location, Geometry) and self.location.type == "Point":
            # Get coordinates directly from Point geometry
            return tuple(self.location.coordinates)

        print(self.location.coordinates)

        # For other cases, you might need more complex logic
        raise ValueError("Cannot extract coordinates from this location type")


class Thing(SensorThingsBase):
    datastreams: list[Datastream] = Field(
        default=[],
        alias="Datastreams",
    )
    location: list[Location] = Field(
        default=[],
        alias="Locations",
    )

    def __str__(self):
        """
        Returns a JSON string representation of the model.

        The JSON string is generated using the `model_dump_json` method with
        `by_alias` set to True and `exclude_none` set to True.

        Returns:
            str: A JSON string representation of the model.
        """
        return self.model_dump_json(by_alias=True, exclude_none=True)
