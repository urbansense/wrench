from typing import TypeVar
from pydantic import BaseModel
from .common.models import EndpointMetadata, TimeFrame, Coordinate

# Define common types used across the package
DocumentType = TypeVar("DocumentType", bound=BaseModel)
LocationType = TypeVar("LocationType", bound=BaseModel)

# Export common type definitions
__all__ = ["DocumentType", "LocationType",
           "EndpointMetadata", "TimeFrame", "Coordinate"]
