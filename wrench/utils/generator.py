# wrench/content/generator.py
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from ollama import Client
from pydantic import BaseModel, Field

from wrench.models import Group


class Content(BaseModel):
    """Represents generated content with name and description."""

    name: str
    description: str


class GeneratorConfig(BaseModel):
    """Configuration for the content generator."""

    @classmethod
    def from_yaml(cls, config: Union[str, Path]) -> "GeneratorConfig":
        with open(config, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls.model_validate(config_dict)

    llm_host: str = Field(description="URL for the LLM host")
    model: str = Field(description="LLM model to use")
    system_prompt: Optional[str] = Field(
        default=None, description="Custom system prompt for content generation"
    )


class ContentGenerator:
    """
    Component responsible for generating descriptive content for data entities.

    This generator uses LLMs to create human-readable names and descriptions
    for various entities in the system.
    """

    def __init__(self, config: Union[GeneratorConfig, str, Path]):
        """
        Initialize the LLM based content generator.

        Args:
            config: LLM configuration for content generation
                provided directly or via path to YAML file
        """
        if isinstance(config, (str, Path)):
            config = GeneratorConfig.from_yaml(config)

        self.config = config
        self.client = Client(host=self.config.llm_host)
        self.model = self.config.model

        # Default system prompt if none provided
        self.system_prompt = self.config.system_prompt or self._get_default_prompt()

    def generate_group_content(self, group: Group, context: dict[str, Any]) -> Content:
        """
        Generate a name and description for a group based on context.

        Args:
            group: The group to generate content for
            context: Dictionary with contextual information (like service_metadata)
                    that helps generate better descriptions

        Returns:
            Content object with name and description

        Example:
            content = generator.generate_group_content(
                group=my_group,
                context={"service_metadata": service_metadata}
            )
        """
        service_metadata = context.get("service_metadata")
        if not service_metadata:
            raise ValueError("service_metadata is required in context")

        prompt = """
            Data:
                Measured Parameter: {measured_param}
                Server Source: {title}
                Sample Data: {data}
            """

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {
                "role": "user",
                "content": prompt.format(
                    measured_param=group.name,
                    title=service_metadata.title,
                    data=[group.items[0]],
                ),
            },
        ]

        response = self.client.chat(
            model=self.model,
            messages=messages,
            format=Content.model_json_schema(),
        )

        if not response.message.content:
            raise RuntimeError("LLM returned no messages")

        return Content.model_validate_json(response.message.content)

    def _get_default_prompt(self) -> str:
        """Return the default system prompt for content generation."""
        return """You are an agent generating name and description for a urban sensor metadata catalog entry
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
