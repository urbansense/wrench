from pydantic import BaseModel


class LLMConfig(BaseModel):
    model: str = "llama3.3:70b-instruct-q4_K_M"
    base_url: str = "http://10.162.246.130:11434/v1"
    api_key: str = "ollama"
