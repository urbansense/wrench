import json

from ollama import Client
from pydantic import BaseModel

from autoreg_metadata.classifier.base import ClassificationResult
from autoreg_metadata.common.models import CommonMetadata, Coordinate

from .models import APIService, DeviceGroup, GeometryType


class CatalogDetails(BaseModel):
    name: str
    description: str


class CatalogGenerator:
    def __init__(self, llm_client: Client, model: str):
        self.llm = llm_client
        self.model = model

    def create_spatial_description(
        self, geometry_type: GeometryType, coor: list[Coordinate]
    ) -> str:
        return json.dumps(
            {
                "type": geometry_type.value,
                # transform each coordinate into a list of linear ring [[lon, lat],...]]
                "coordinates": [[c.to_list() for c in coor]],
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
        self, api_service: APIService, data: ClassificationResult
    ) -> list[DeviceGroup]:
        device_groups = []

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

        for category, records in data.classification_result.items():
            print(category)
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt.format(
                        measured_param=category,
                        title=api_service.title,
                        data=[records[0].content],
                    ),
                },
            ]
            response = self.llm.chat(
                model=self.model,
                messages=messages,
                format=CatalogDetails.model_json_schema(),
            )
            print(response.message.content)
            catalog_details = CatalogDetails.model_validate_json(
                response.message.content
            )

            device_group = DeviceGroup.from_api_service(
                api_service=api_service,
                # convert to lower and replace space with underscores
                name=catalog_details.name,
                tags=[{"name": tag} for tag in data.parent_classes[category]],
                description=catalog_details.description,
                resources=[
                    {
                        "name": f"URL for {catalog_details.name}",
                        "description": f"URL provides a list of all data associated with the category {category}",
                        "format": "JSON",
                        "url": "mock-url.com",
                    }
                ],
            )

            device_groups.append(device_group)

        return device_groups
