from datetime import datetime
from typing import List, Optional, Tuple

from pydantic import BaseModel


class TimeFrame(BaseModel):
    start_time: datetime
    latest_time: datetime


class Coordinate(BaseModel):
    longitude: float
    latitude: float


class EnrichedMetadata(BaseModel):
    timeframe: Optional[TimeFrame] = None
    geographical_extent: Optional[Tuple[Coordinate, Coordinate]] = None
    sensor_types: Optional[List[str]] = None
    measurements: Optional[List[str]] = None
    language: Optional[str] = None
    author: Optional[str] = None
