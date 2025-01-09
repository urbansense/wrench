from autoreg_metadata.harvester.frost import FrostHarvester
from autoreg_metadata.harvester.frost.harvester import with_translator, with_location_model
from autoreg_metadata.harvester.frost.models import GenericLocation
from typing import Dict, Tuple

from pydantic import BaseModel


class Geometry(BaseModel):
    type: str = "Point"
    coordinates: Tuple[float, float]  # lng, lat


class Feature(BaseModel):
    type: str
    properties: Dict
    geometry: Geometry


class MyLocation(GenericLocation):
    location: Feature

    def get_coordinates(self) -> Tuple[float, float]:
        return self.location.geometry.coordinates


harvester = FrostHarvester(
    "https://iot.hamburg.de/v1.1",
    with_location_model(MyLocation)
)


em, _ = harvester.enrich()
print(em.geographical_extent)
print(em.timeframe)
