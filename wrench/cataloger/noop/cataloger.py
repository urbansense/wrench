from wrench.cataloger.base import BaseCataloger
from wrench.models import CommonMetadata


class NoopCataloger(BaseCataloger):
    """Noop cataloger for testing purposes."""

    def __init__(self, endpoint: str = "", api_key: str = ""):
        """Initializes the noop cataloger."""
        super().__init__(endpoint=endpoint, api_key=api_key)

    def register(
        self,
        service: CommonMetadata,
        groups: list[CommonMetadata],
        managed_entries: list[str] | None,
    ) -> list[str]:
        return []
