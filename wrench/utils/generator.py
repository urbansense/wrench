# wrench/content/generator.py
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from ollama import Client
from pydantic import BaseModel, Field

from wrench.models import Group


class Content(BaseModel):
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
            The device group name is **{group_name}**, it contains devices found in the
            source API service **{title}**. Here are some information about the devices
            within this group

            {data}

            """

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {
                "role": "user",
                "content": prompt.format(
                    group_name=group.name,
                    title=service_metadata.title,
                    data=[
                        dev.model_dump_json(
                            include=["name", "description", "datastreams"]
                        )
                        for dev in group.devices[0 : min(len(group.devices), 3)]
                    ],
                ),
            },
        ]

        response = self.client.chat(
            model=self.model,
            messages=messages,
            format=Content.model_json_schema(),
            options={"temperature": 0},
        )

        if not response.message.content:
            raise RuntimeError("LLM returned no messages")

        return Content.model_validate_json(response.message.content)

    def _get_default_prompt(self) -> str:
        """Return the default system prompt for content generation."""
        return """
            You are an agent with expertise in naming and describing sensor groups based on the group information and its sample data.
            Generate names and descriptions based on solely the information given by the user.

            Respond in ENGLISH. Give as much information as you can in the title and description, without making up unverifiable
            information. The description should be about 3-4 sentences long, and describe what kind of data the group contains,
            based on the samples. You can add sensor information as well as measured parameters to your description too.

            Make sure that you give information about the source from which the data is retrieved, in the title. If the source
            is for example "City A FROST Server", be sure to include this information in the title.
        """
