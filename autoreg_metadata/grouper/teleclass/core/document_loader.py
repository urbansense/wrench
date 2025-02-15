import json
from pathlib import Path
from typing import Protocol, Union

from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from autoreg_metadata.common.models import Item
from autoreg_metadata.grouper.teleclass.core.models import DocumentMeta


class DocumentLoader(Protocol):
    def load(self, encoder: SentenceTransformer) -> list[DocumentMeta]:
        pass


class JSONDocumentLoader:
    """
    A document loader for JSON files that loads and processes documents into a list of DocumentMeta objects.

    Attributes:
        file_path (Union[str, Path]): The path to the JSON file to be loaded.

    Methods:
        __init__(file_path: Union[str, Path]):
            Initializes the JSONDocumentLoader with the given file path.

        load(encoder: SentenceTransformer) -> list[DocumentMeta]:
            Loads the JSON file, processes the documents, and returns a list of DocumentMeta objects.
            Raises FileNotFoundError if the JSON file does not exist.
            Raises ValueError if the JSON file does not contain a list of documents.
    """

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)

    def load(self, encoder: SentenceTransformer) -> list[DocumentMeta]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {self.file_path}")

        with open(self.file_path, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of documents")

        return [
            DocumentMeta(
                id=str(idx),
                content=json.dumps(doc),
                embeddings=encoder.encode(json.dumps(doc)),
            )
            for idx, doc in enumerate(data)
        ]


class ModelDocumentLoader:
    """
    A class to load and process documents that are instances of Pydantic BaseModel.

    Attributes:
        documents (list[BaseModel]): A list of Pydantic BaseModel instances.

    Methods:
        __init__(documents: list[BaseModel]):
            Initializes the ModelDocumentLoader with a list of BaseModel instances.

        load(encoder: SentenceTransformer) -> list[DocumentMeta]:
            Loads the documents, encodes their content using the provided encoder,
            and returns a list of DocumentMeta instances.
    """

    def __init__(self, documents: list[Item]):
        if not isinstance(documents, list) or not all(
            isinstance(doc, BaseModel) for doc in documents
        ):
            raise TypeError("documents must be a list of Item instances")
        self.documents = documents

    def load(self, encoder: SentenceTransformer) -> list[DocumentMeta]:
        return [
            DocumentMeta(
                id=doc.id,
                content=doc.model_dump_json(),
                embeddings=encoder.encode(doc.model_dump_json()),
            )
            for doc in self.documents
        ]
