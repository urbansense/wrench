from abc import ABC, abstractmethod
from pathlib import Path

import yaml
from ollama import Client
from pydantic import BaseModel, Field

from wrench.catalogger.base import BaseCatalogger
from wrench.grouper.base import Group
from wrench.harvester.base import BaseHarvester
from wrench.log import logger
from wrench.models import CatalogEntry, CommonMetadata


class AdapterConfig(BaseModel):
    @classmethod
    def from_yaml(cls, config: str | Path) -> "AdapterConfig":
        with open(config, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls.model_validate(config_dict)

    llm_host: str = Field(
        description="Ollama host endpoint used to generate name and descriptions for catalog entries"
    )

    llm_model: str = Field(
        description="Name of Ollama model to use to generate the name and description"
    )


class BaseCatalogAdapter[H: BaseHarvester, C: BaseCatalogger](ABC):
    """H = Type of Harvester, C = Type of Catalogger."""

    def __init__(self, llm_host: str, model: str):
        """
        Initializes the base adapter with the given language model host and model name.

        Args:
            llm_host (str): The host address of the language model.
            model (str): The name of the model to be used.
        """
        self.llm = Client(host=llm_host)
        self.model = model
        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def create_service_entry(self, metadata: CommonMetadata) -> CatalogEntry:
        """
        Creates a service entry in the catalog using the provided metadata.

        Args:
            metadata (CommonMetadata): The metadata information
                                       required to create the catalog entry.

        Returns:
            CatalogEntry: The created catalog entry.
        """
        pass

    @abstractmethod
    def create_group_entry(
        self, service_entry: CatalogEntry, group: Group
    ) -> CatalogEntry:
        """
        Creates a new group entry in the catalog.

        Args:
            service_entry (CatalogEntry): The catalog entry representing the service.
            group (Group): The group to which the service entry will be added.

        Returns:
            CatalogEntry: The newly created catalog entry for the group.
        """
        pass

    def _generate_catalog_data(self, service_entry, group) -> CatalogEntry:
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

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt.format(
                    measured_param=group.name,
                    title=service_entry.name,
                    data=[group.items[0]],
                ),
            },
        ]
        response = self.llm.chat(
            model=self.model,
            messages=messages,
            format=CatalogEntry.model_json_schema(),
        )
        if not response.message.content:
            raise RuntimeError("LLM returned no messages")
        return CatalogEntry.model_validate_json(response.message.content)
