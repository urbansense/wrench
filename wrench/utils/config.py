from pydantic import AliasChoices, BaseModel, Field


class LLMConfig(BaseModel):
    """Unified configuration for LLM services.

    Supports both 'base_url' and 'host' for backwards compatibility.
    """

    base_url: str = Field(
        validation_alias=AliasChoices("base_url", "host"),
        description="LLM service URL",
    )
    model: str = Field(
        default="llama3.3:70b-instruct-q4_K_M",
        description="Model to use for LLM operations",
    )
    api_key: str = Field(
        default="ollama",
        description="API key for the LLM service",
    )
    temperature: float = Field(
        default=0.0,
        description="Temperature for LLM generation",
    )
    prompt: str | None = Field(
        default=None,
        description="Optional prompt template",
    )
