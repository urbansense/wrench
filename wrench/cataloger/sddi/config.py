from pydantic import BaseModel, Field


class SDDIConfig(BaseModel):
    """Configuration for SDDI Cataloger."""

    base_url: str = Field(description="Base URL for the SDDI CKAN server")

    api_key: str = Field(
        description="API key to be access the Action API of the SDDI CKAN server"
    )

    owner_org: str = Field(
        description="Owner organization under which the data will be registered"
    )
