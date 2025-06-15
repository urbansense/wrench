from pydantic import BaseModel, Field


class PaginationConfig(BaseModel):
    page_delay: float = Field(
        default=0.1, description="Delay between pagination requests in seconds"
    )
    timeout: int = Field(default=60, description="Request timeout in seconds")
    batch_size: int = Field(default=100, description="Number of items per page")
