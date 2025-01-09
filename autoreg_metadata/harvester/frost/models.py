from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from abc import ABC, abstractmethod

model_config = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    from_attributes=True,
)


class FrostBase(BaseModel):
    """Base mixin for common fields for relevant SensorThings API Entities"""

    model_config = model_config
    id: int = Field(alias="@iot.id")
    name: str
    description: str
    properties: Optional[Dict[str, Any]] = None


class Sensor(FrostBase):
    encoding_type: str


class ObservedProperty(FrostBase):
    pass


class Datastream(FrostBase):
    unit_of_measurement: Dict
    observed_area: Optional[Dict] = None
    phenomenon_time: Optional[str] = None
    result_time: Optional[str] = None
    sensor: Sensor = Field(alias="Sensor")
    observed_property: Optional[ObservedProperty] = Field(
        default=None, alias="ObservedProperty"
    )


class GenericLocation(ABC, FrostBase):
    encoding_type: str

    @abstractmethod
    def get_coordinates(self) -> Tuple[float, float]:
        pass


class GeoPoint(BaseModel):
    """Represents a GeoJSON Point Geometry"""

    type: str = "Point"
    coordinates: Tuple[float, float]  # longitude, latitude


class Location(GenericLocation):
    location: GeoPoint

    def get_coordinates(self) -> Tuple[float, float]:
        return self.location.coordinates


class Thing(FrostBase):
    datastreams: List[Datastream] = Field(alias="Datastreams")

    def __str__(self):
        return self.model_dump_json(by_alias=True, exclude_none=True)
