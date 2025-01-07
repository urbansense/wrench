from datetime import datetime
from typing import List

from pydantic import BaseModel


class TimeFrame(BaseModel):
    start_time: datetime
    latest_time: datetime


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class EnrichedMetadata(BaseModel):
    timeframe: TimeFrame
    geographical_extent: Coordinates
    sensor_types: List[str]
    measurements: List[str]
    language: str
    author: str
