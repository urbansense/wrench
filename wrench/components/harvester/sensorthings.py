from pydantic import BaseModel, validate_call

from wrench.components.decorators import register_component
from wrench.components.types import Items
from wrench.harvester.sensorthings import (
    SensorThingsHarvester,
)
from wrench.pipeline.models import Component


class SensorThingsHarvesterConfig(BaseModel):
    """Configuration for SensorThings harvester."""

    base_url: str
    title: str
    description: str
    pagination_config: dict | None = None
    translator_config: dict | None = None


@register_component("harvester", "sensorthings")
class SensorThingsHarvesterComponent(Component):
    """SensorThings API harvester component."""

    def __init__(
        self,
        base_url: str,
        pagination_config=None,
        translator=None,
    ):
        """Wraps SensorThingsHarvester in a pipeline component."""
        self.harvester = SensorThingsHarvester(
            base_url=base_url,
            pagination_config=pagination_config,
            translator=translator,
        )

    @validate_call
    async def run(self) -> Items:
        """Run the harvester and return structured results."""
        try:
            # Directly get items from the harvester
            items = self.harvester.return_items()

            return Items(devices=[item.model_dump() for item in items])
        except Exception:
            # Re-raise to ensure pipeline knows this component failed
            raise
