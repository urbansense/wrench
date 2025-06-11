from typing import Sequence

from sentence_transformers import SentenceTransformer

from wrench.grouper.teleclass.core.models import Document
from wrench.models import Device


class ModelDocumentLoader:
    """
    A class to load and process documents that are instances of Device.

    Attributes:
        documents (Sequence[Device]): A list of dict representing device instances.

    Methods:
        __init__(documents: Sequence[Device]):
            Initializes the ModelDocumentLoader with a list of device instances.

        load(encoder: SentenceTransformer) -> list[DocumentMeta]:
            Loads the documents, encodes their content using the provided encoder,
            and returns a list of DocumentMeta instances.
    """

    def __init__(self, documents: Sequence[Device]):
        """
        Initialize the DocumentLoader with a list of devices.

        Args:
            documents (Sequence[Device]): A list of devices.

        Raises:
            TypeError: If documents is not a list or if any element
                       in documents is not an instance of item.
        """
        if not isinstance(documents, list) or not all(
            isinstance(doc, Device) for doc in documents
        ):
            raise TypeError(
                f"""documents must be a list of Device instances, got list of \
                    {type(documents)}"""
            )
        self.documents = documents

    def load(self, encoder: SentenceTransformer) -> list[Document]:
        return [
            Document(
                id=doc.id,
                content=doc.model_dump_json(),
                embeddings=encoder.encode(doc.model_dump_json(), convert_to_numpy=True),
            )
            for id, doc in enumerate(self.documents)
        ]
