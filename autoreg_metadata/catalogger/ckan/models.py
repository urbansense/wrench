from enum import Enum

from pydantic import BaseModel, computed_field


class GeometryType(Enum):
    point = "Point"
    line_string = "LineString"
    linear_ring = "LinearRing"
    polygon = "Polygon"
    multi_point = "MultiPoint"
    multi_linestring = "MultiLineString"
    multi_polygon = "MultiPolygon"
    multi_geometry = "MultiGeometry"


class SDDICategory(Enum):
    online_service = "online-service"
    device = "device"


class BaseDataset(BaseModel):
    # required
    name: str
    notes: str
    owner_org: str
    title: str
    # optional with predefined defaults
    api_url: str = ""
    author: str = ""
    author_email: str = ""
    end_collection_date: str = ""
    groups: list[dict] = []
    language: str = ""
    licence_agreement: list[str] = ["licence_agreement_check"]
    license_id: str = "Apache-2.0"
    license_title: str = "Apache License 2.0"
    license_url: str = "https://www.apache.org/licenses/LICENSE-2.0"
    private: bool = False
    relationships_as_object: list[dict] = []
    relationships_as_subject: list[dict] = []
    spatial: str = ""
    state: str = "active"
    tags: list[dict] = []


class APIService(BaseDataset):
    groups: list[dict] = [{"name": SDDICategory.online_service.value}]

    @computed_field  # type: ignore[misc]
    @property
    def resources(self) -> list[dict]:
        return [
            {
                "name": "API Service URL",
                "description": "URL for the API service",
                "format": "api",
                "url": self.api_url,
            }
        ]


class DeviceGroup(APIService):
    groups: list[dict] = [{"name": SDDICategory.device.value}]
    resource: None = None

    @classmethod
    def from_api_service(cls, api_service: APIService) -> "DeviceGroup":
        # Get all fields from api_service except 'groups' and 'resources'
        data = api_service.model_dump(exclude={"groups", "resources"})
        return cls(**data)
