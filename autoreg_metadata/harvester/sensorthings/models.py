from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

model_config = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    from_attributes=True,
)


class SensorThingsBase(BaseModel):
    """Base mixin for common fields for relevant SensorThings API Entities"""

    model_config = model_config
    id: int = Field(alias="@iot.id")
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
    """Represents a GeoJSON Point Geometry"""

    type: str = "Point"
    coordinates: tuple[float, float]  # longitude, latitude


class GenericLocation(ABC, SensorThingsBase):
    encoding_type: str

    @abstractmethod
    def get_coordinates(self) -> tuple[float, float]:
        pass


class Location(GenericLocation):
    location: GeoPoint

    def get_coordinates(self) -> tuple[float, float]:
        return self.location.coordinates


class Thing(SensorThingsBase):
    datastreams: list[Datastream] = Field(default=None, alias="Datastreams")
    location: list[Location] = Field(default=None, alias="Locations")

    def __str__(self):
        return self.model_dump_json(by_alias=True, exclude_none=True)
