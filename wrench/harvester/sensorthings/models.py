from typing import Any

import geojson
import xxhash
from geojson import Feature, FeatureCollection
from geojson.geometry import Geometry
from geojson.utils import coords
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

model_config = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    from_attributes=True,
    coerce_numbers_to_str=True,
)


class SensorThingsBase(BaseModel):
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


class Location(SensorThingsBase):
    encoding_type: str
    location: Feature | FeatureCollection | Geometry = Field(
        description="GeoJSON location data as Feature, FeatureCollection, or Geometry"
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("location", mode="before")
    @classmethod
    def validate_geojson(cls, v):
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
        return list(coords(self.location))


class Thing(SensorThingsBase):
    datastreams: list[Datastream] = Field(
        default=[],
        alias="Datastreams",
    )
    location: list[Location] = Field(
        default=[],
        alias="Locations",
    )

    def __str__(self) -> str:
        return self.model_dump_json(by_alias=True, exclude_none=True)

    def __hash__(self) -> str:
        return xxhash.xxh32(str(self)).hexdigest()
