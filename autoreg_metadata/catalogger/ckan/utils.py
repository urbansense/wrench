import json

from .models import GeometryType, APIService
from autoreg_metadata.common.models import Coordinate, CommonMetadata


def create_spatial_description(geometry_type: GeometryType, coor: list[Coordinate]) -> str:
    print(len(coor))
    return json.dumps({
        "type": geometry_type.value,
        # transform each coordinate into a list [lon, lat]
        "coordinates": [[c.to_list() for c in coor]],
    }, indent=3)


def create_api_service(metadata: CommonMetadata) -> APIService:

    spatial_desc = create_spatial_description(
        GeometryType.polygon, list(metadata.spatial_extent))

    # set a default owner for now HANDLE THIS LATER
    owner = metadata.owner or "lehrstuhl-fur-geoinformatik"

    return APIService(
        api_url=metadata.endpoint_url,
        name=metadata.identifier,
        notes=metadata.description,
        owner_org=owner,
        title=metadata.title,
        tags=[{"name": tag} for tag in metadata.tags],
        spatial=spatial_desc,
    )
