from typing import Any

import xxhash
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from wrench.models import Location as WrenchLocation

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


class Location(SensorThingsBase, WrenchLocation):
    pass


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
