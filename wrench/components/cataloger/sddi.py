from typing import Sequence

from pydantic import BaseModel, validate_call

from wrench.cataloger.sddi import SDDICataloger
from wrench.components.decorators import register_component
from wrench.models import CommonMetadata
from wrench.pipeline.models import Component, DataModel


class CatalogerStatus(DataModel):
    success: bool = False
    groups: list[str]


class SDDICatalogerConfig(BaseModel):
    """Configuration for SensorThings harvester."""

    base_url: str
    title: str
    description: str
    pagination_config: dict | None = None
    translator_config: dict | None = None


@register_component("harvester", "sensorthings")
class SDDICatalogerComponent(Component):
    """SensorThings API harvester component."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        owner_org: str = "lehrstuhl-fur-geoinformatik",
    ):
        """Wraps SensorThingsHarvester in a pipeline component."""
        self.cataloger = SDDICataloger(
            base_url=base_url,
            api_key=api_key,
            owner_org=owner_org,
        )

    @validate_call
    async def run(
        self, service_metadata: CommonMetadata, group_metadata: Sequence[CommonMetadata]
    ) -> CatalogerStatus:
        """Run the cataloger and register metadata."""
        try:
            # Directly get items from the harvester
            self.cataloger.register(service=service_metadata, groups=group_metadata)
            return CatalogerStatus(
                success=True, groups=[group.identifier for group in group_metadata]
            )
        except Exception:
            # Re-raise to ensure pipeline knows this component failed
            raise
