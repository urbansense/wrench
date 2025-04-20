from geojson.geometry import Geometry
from pydantic import BaseModel


class Device(BaseModel):
    code: str
    name: str
    description: str
    registered: None = None
    timezone: str
    geometry: Geometry
    additional_properties: None = None
    sensors_url: str
