from pydantic import BaseModel


class LLMConfig(BaseModel):
    base_url: str
    model: str = "llama3.3:70b-instruct-q4_K_M"
    api_key: str = "ollama"
