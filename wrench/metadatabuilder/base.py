from typing import Protocol

from wrench.models import CommonMetadata, Group


class BaseMetadataBuilder[T](Protocol):
    def build_service_metadata(self, source_data: list[T]) -> CommonMetadata:
        """
        Retrieves metadata for service endpoint.

        Returns:
            CommonMetadata: Data model conformant to catalog requirement.
        """
        pass

    def build_group_metadata(self, group: Group) -> CommonMetadata:
        """
        Builds metadata for groups returned by Grouper.

        Returns:
            CommonMetadata: Data model conformant to catalog requirement.
        """
        pass
