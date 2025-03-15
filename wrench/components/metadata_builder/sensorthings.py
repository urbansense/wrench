from pydantic import BaseModel, validate_call

from wrench.components.decorators import register_component
from wrench.components.types import Groups, Items
from wrench.metadatabuilder.sensorthings import SensorThingsMetadataBuilder
from wrench.models import CommonMetadata
from wrench.pipeline.models import Component, DataModel
from wrench.utils.generator import ContentGenerator


class Metadata(DataModel):
    service_metadata: CommonMetadata
    group_metadata: list[CommonMetadata]


class SensorThingsMetadataBuilderConfig(BaseModel):
    """Configuration for SensorThings metadata builder."""

    base_url: str
    title: str
    description: str
    llm_host: str
    model: str


@register_component("metadatabuilder", "sensorthings")
class SensorThingsMetadataBuilderComponent(Component):
    """SensorThings API harvester component."""

    def __init__(
        self,
        base_url: str,
        title: str,
        description: str,
        content_generator: ContentGenerator,
    ):
        """Wraps SensorThingsHarvester in a pipeline component."""
        self.metadatabuilder = SensorThingsMetadataBuilder(
            base_url=base_url,
            title=title,
            description=description,
            content_generator=content_generator,
        )

    @validate_call
    async def run(self, items: Items, groups: Groups) -> Metadata:
        """Run the harvester and return structured results."""
        try:
            service_metadata = self.metadatabuilder.build_service_metadata(
                items.devices
            )

            group_metadata = [
                self.metadatabuilder.build_group_metadata(group)
                for group in groups.groups
            ]

            return Metadata(
                service_metadata=service_metadata, group_metadata=group_metadata
            )

        except Exception:
            # Re-raise to ensure pipeline knows this component failed
            raise
