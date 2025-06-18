from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from wrench.models import Group
from wrench.utils.config import LLMConfig
from wrench.utils.prompt_manager import PromptManager

SYSTEM_PROMPT = PromptManager.get_prompt("generator_system_prompt.txt")


class Content(BaseModel):
    name: str
    description: str


class ContentGenerator:
    """
    Component responsible for generating descriptive content for data entities.

    This generator uses LLMs to create human-readable names and descriptions
    for various entities in the system.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize the LLM based content generator.

        Args:
            config: LLM configuration for content generation
        """
        self.client = OpenAI(base_url=config.base_url, api_key=config.api_key)
        self.model = config.model

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
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt.format(
                    group_name=group.name,
                    title=service_metadata.title,
                    data=[
                        dev.model_dump_json(
                            include=[
                                "name",
                                "description",
                                "datastreams",
                                "sensors",
                                "observed_properties",
                            ]
                        )
                        for dev in group.devices[0 : min(len(group.devices), 3)]
                    ],
                ),
            },
        ]

        response = self.client.beta.chat.completions.parse(
            messages=messages,
            model=self.model,
            response_format=Content,
            temperature=0,
        )

        if not response.choices[0].message.parsed:
            raise RuntimeError("LLM returned no messages")

        return response.choices[0].message.parsed
