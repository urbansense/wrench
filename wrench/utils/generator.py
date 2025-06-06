from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from wrench.models import Group


class Content(BaseModel):
    name: str
    description: str


class LLMConfig(BaseModel):
    base_url: str
    model: str = "llama3.3:70b-instruct-q4_K_M"
    api_key: str = "ollama"


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

        self.system_prompt = self._get_default_prompt()

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

        response = self.client.beta.chat.completions.parse(
            messages=messages,
            model=self.model,
            response_format=Content,
            temperature=0,
        )

        if not response.choices[0].message.parsed:
            raise RuntimeError("LLM returned no messages")

        return response.choices[0].message.parsed

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
