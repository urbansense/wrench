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
    url: str | None = None
    author: str = ""
    author_email: str = ""
    end_collection_date: str = ""  # necessary to properly register entries
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
    type: str = "dataset"


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
                "url": self.url,
            }
        ]


class DeviceGroup(BaseDataset):
    groups: list[dict] = [{"name": SDDICategory.device.value}]
    resources: list[dict] = []

    @classmethod
    def from_api_service(
        cls,
        api_service: APIService,
        name: str,
        description: str,
        tags: list[dict[str, str]],
        resources: list = None,
    ) -> "DeviceGroup":
        # Get all fields from api_service except 'groups' and 'resources'
        ckan_name = name.lower().strip().replace(" ", "_")
        data = api_service.model_dump(exclude={"groups", "resources"})
        data.update(
            {
                "name": ckan_name,
                "title": name,
                "notes": description,
                "tags": tags,
                "resources": resources or [],
            }
        )
        return cls(**data)
