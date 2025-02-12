import json

from ollama import Client
from pydantic import BaseModel

from autoreg_metadata.common.models import CommonMetadata, Coordinate
from autoreg_metadata.grouper.base import Group
from autoreg_metadata.grouper.teleclass.core.models.enrichment_models import (
    DocumentMeta,
)
from autoreg_metadata.harvester.sensorthings.models import Thing
from autoreg_metadata.log import logger

from .models import APIService, DeviceGroup, GeometryType


class CatalogDetails(BaseModel):
    name: str
    description: str


class CatalogGenerator:
    def __init__(self, llm_client: Client, model: str):
        self.llm = llm_client
        self.model = model
        self.logger = logger.getChild(self.__class__.__name__)

    def create_spatial_description(
        self, geometry_type: GeometryType, coor: list[Coordinate]
    ) -> str:
        """
        Creates a spatial description in GeoJSON format.

        Args:
            geometry_type (GeometryType): The type of geometry (e.g., Point, LineString, Polygon).
            coor (list[Coordinate]): A list of Coordinate objects representing the geometry.

        Returns:
            str: A JSON string representing the spatial description in GeoJSON format.
        """
        if geometry_type.value == "Polygon":
            coordinates = [[c.to_list() for c in coor]]
        if geometry_type.value == "MultiPoint":
            coordinates = [c.to_list() for c in coor]

        return json.dumps(
            {
                "type": geometry_type.value,
                # transform each coordinate into a list of linear ring [[lon, lat],...]]
                "coordinates": coordinates,
            },
            indent=3,
        )

    def create_api_service(self, metadata: CommonMetadata) -> APIService:

        spatial_desc = self.create_spatial_description(
            GeometryType.polygon, list(metadata.spatial_extent)
        )

        # set a default owner for now HANDLE THIS LATER
        owner = metadata.owner or "lehrstuhl-fur-geoinformatik"

        return APIService(
            url=metadata.endpoint_url,
            name=metadata.identifier,
            notes=metadata.description,
            owner_org=owner,
            title=metadata.title,
            tags=[{"name": tag} for tag in metadata.tags],
            spatial=spatial_desc,
        )

    def create_device_groups(
        self, api_service: APIService, groups: list[Group[DocumentMeta]]
    ) -> list[DeviceGroup]:

        self.logger.info("Creating device groups")

        device_groups = []

        domain_groups = [
            "administration",
            "mobility",
            "environment",
            "agriculture",
            "urban-planning",
            "health",
            "energy",
            "information-technology",
            "tourism",
            "living",
            "education",
            "construction",
            "culture",
            "trade",
            "craft",
            "work",
        ]

        system_prompt = """You are an agent generating name and description for a urban sensor metadata catalog entry
              based on solely the information given by the user, do not add extra information which is not given by the user.
              Here are some examples of name and descriptions:
              Request:
                Data:
                  Measured Parameter: Bicycle Count
                  Server Source: City X FROST Server
                  Sample Data: {
                    "@iot.selfLink": "https://city-x.com/v1.1/Things(72)",
                    "@iot.id": 72,
                    "description": "Bicycle Count (Location: XYZ)",
                    "name": "Bicycle Count XYZ",
                    "properties": {
                        "operation_status": "inactive",
                        "deviceIDniota": 4174,
                        "keywords": ["Bicycle", "Count"],
                        "language": "en",
                        "owner": "Transportation Minister of City X",
                        "ownerThing": "Transportation Minister of City X",
                        "topic": "Bicycle count"
                    },
                  }
              Response:
              {{
                "name": "Bicycle Counts in City X",
                "description": "Bicycle counts conducted by Transportation Minister of City X around City X at key locations."
              }}"""

        prompt = """
            Data:
                Measured Parameter: {measured_param}
                Server Source: {title}
                Sample Data: {data}
            """

        for group in groups:
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt.format(
                        measured_param=group.name,
                        title=api_service.title,
                        data=[group.items[0].content],
                    ),
                },
            ]
            response = self.llm.chat(
                model=self.model,
                messages=messages,
                format=CatalogDetails.model_json_schema(),
            )
            catalog_details = CatalogDetails.model_validate_json(
                response.message.content
            )

            coord = []

            for r in group.items:
                thing_with_location = Thing.model_validate_json(r.content)
                if not thing_with_location.location:
                    continue
                for loc in thing_with_location.location:
                    lon, lat = loc.get_coordinates()
                    coord.append(Coordinate(longitude=lon, latitude=lat))

            self.logger.info("Finished getting things with locations")

            device_group = DeviceGroup.from_api_service(
                api_service=api_service,
                # convert to lower and replace space with underscores
                name=catalog_details.name,
                tags=[{"name": tag} for tag in group.parent_classes],
                description=catalog_details.description,
                resources=[
                    {
                        "name": f"URL for {catalog_details.name}",
                        "description": f"URL provides a list of all data associated with the category {group.name}",
                        "format": "JSON",
                        "url": "mock-url.com",
                    }
                ],
            )
            # extend group with any of the domain names from classifier (e.g. mobility)
            device_group.groups.extend(
                [{"name": dom} for dom in group.parent_classes if dom in domain_groups]
            )

            device_group.spatial = self.create_spatial_description(
                geometry_type=GeometryType.multi_point, coor=coord
            )

            device_groups.append(device_group)

        return device_groups
