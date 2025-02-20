from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class PaginationConfig(BaseModel):
    """Configuration for pagination behavior."""

    page_delay: float = Field(
        default=0.1, description="Delay between pagination requests in seconds"
    )
    timeout: int = Field(default=60, description="Request timeout in seconds")
    batch_size: int = Field(default=100, description="Number of items per page")


class TranslatorConfig(BaseModel):
    """Configuration for translation service."""

    url: str = Field(description="Base URL for the translation service")
    source_lang: str | None = Field(default=None, description="Source language code")


class SensorThingsConfig(BaseModel):
    """Main configuration for SensorThings harvester."""

    @classmethod
    def from_yaml(cls, config: str | Path) -> "SensorThingsConfig":
        """
        Create a SensorThingsConfig instance from a YAML file.

        Args:
            config (str | Path): The path to the YAML configuration file.

        Returns:
            SensorThingsConfig: SensorThingsConfig with the data from the YAML file.

        Raises:
            FileNotFoundError: If the specified YAML file does not exist.
            yaml.YAMLError: If there is an error parsing the YAML file.
        """
        with open(config, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls.model_validate(config_dict)

    base_url: str = Field(description="Base URL for the SensorThings server")

    identifier: str = Field(
        description="""Identifier for registering into backend,
                    must be lowercase and separated by underscores"""
    )

    title: str = Field(
        description="The title which should be used for entry in the catalog"
    )

    description: str = Field(
        description="The description which should be used for entry in the catalog"
    )

    # optional

    translator: TranslatorConfig | None = Field(
        default=None, description="Translation service configuration"
    )
    pagination: PaginationConfig = Field(
        default_factory=PaginationConfig, description="Pagination settings"
    )
    default_limit: int = Field(
        default=-1, description="Default limit for fetching items (-1 for no limit)"
    )
