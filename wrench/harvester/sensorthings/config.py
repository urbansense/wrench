from typing import Literal

from pydantic import BaseModel, Field


class PaginationConfig(BaseModel):
    page_delay: float = Field(
        default=0.1, description="Delay between pagination requests in seconds"
    )
    timeout: int = Field(default=60, description="Request timeout in seconds")
    batch_size: int = Field(default=100, description="Number of items per page")


class TranslatorConfig(BaseModel):
    translator_type: Literal["libre_translate"] = Field(
        description="Type of translator to use"
    )
    url: str = Field(description="Base URL for the translation service")
    source_lang: str | None = Field(default=None, description="Source language code")
