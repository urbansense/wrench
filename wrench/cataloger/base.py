from abc import ABC, abstractmethod
from typing import Sequence

from wrench.log import logger
from wrench.models import CommonMetadata


class BaseCataloger(ABC):
    def __init__(self, endpoint: str, api_key: str):
        """
        Initializes the base class with the given endpoint and API key.

        Args:
            endpoint (str): The API endpoint URL.
            api_key (str): The API key for authentication.
        """
        self.endpoint = endpoint
        self.api_key = api_key

        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def register(
        self,
        service: CommonMetadata,
        groups: Sequence[CommonMetadata],
        managed_entries: list[str] | None,
    ) -> list[str]:
        """
        Registers the service and its groups to the catalog.

        Args:
            service (CommonMetadata): The service to be registered.
            groups (Sequence(CommonMetadata)): The groups which should be
                registered under the service.
            managed_entries: list(str): The entries created by the catalogger.

        Returns:
            list(str): The list of keys or URLs the resources are registered under.
        """
        pass
