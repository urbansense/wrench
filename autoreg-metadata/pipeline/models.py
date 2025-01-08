from datetime import datetime
from typing import List, Set, Tuple, Optional

from pydantic import BaseModel

from harvester.frost import Thing


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


class ClassifiedThing(Thing):
    classification: Set[str]
    confidence: float
