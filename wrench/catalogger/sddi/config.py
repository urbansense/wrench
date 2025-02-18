import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class SDDIConfig(BaseModel):
    """Configuration for SDDI Catalogger"""

    @classmethod
    def from_yaml(cls, config: str | Path) -> "SDDIConfig":
        with open(config, "r") as f:
            config_str = os.path.expandvars(f.read())
            config_dict = yaml.safe_load(config_str)
        return cls.model_validate(config_dict)

    base_url: str = Field(description="Base URL for the SDDI CKAN server")

    api_key: str = Field(
        description="API key to be access the Action API of the SDDI CKAN server"
    )

    owner_org: str = Field(
        description="Owner organization under which the data will be registered"
    )

    llm_host: str = Field(
        description="Ollama host endpoint used to generate name and descriptions for catalog entries"
    )

    llm_model: str = Field(
        description="Name of Ollama model to use to generate the name and description"
    )
