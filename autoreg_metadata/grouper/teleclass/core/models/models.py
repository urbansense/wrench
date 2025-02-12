from typing import TypeVar

import numpy as np
from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound=BaseModel)


class DocumentMeta(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    embeddings: np.ndarray | None = None
    content: str
    # Core classes set after LLM enrichment
    initial_core_classes: set[str] | None = None
