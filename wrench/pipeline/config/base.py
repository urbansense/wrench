from typing import Any, Optional

from pydantic import BaseModel, PrivateAttr

from wrench.pipeline.pipeline import Pipeline


class AbstractConfig(BaseModel):
    """Base class for all pipeline configurations."""

    _global_data: dict[str, Any] = PrivateAttr({})

    def resolve_param(self, param: Any) -> Any:
        """Resolve parameter values from their definition."""
        # Implementation similar to Neo4j's param resolver
        pass

    def parse(self, resolved_data: Optional[dict[str, Any]] = None) -> Any:
        """Parse the configuration into concrete objects."""
        raise NotImplementedError()


class PipelineConfig(AbstractConfig):
    """Configuration for a custom pipeline."""

    component_config: dict[str, dict[str, Any]]
    connection_config: list[dict[str, Any]]

    def parse(self, resolved_data: Optional[dict[str, Any]] = None) -> Pipeline:
        """Parse config into a Pipeline instance."""
        pipeline = Pipeline()
        # Create and add components based on config
        # Set up connections based on config
        return pipeline
