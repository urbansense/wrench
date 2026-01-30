"""Component configuration using registries."""

from __future__ import annotations

from typing import Any, Union

from pydantic import BaseModel, ConfigDict, field_validator

from wrench.cataloger import CATALOGERS, BaseCataloger
from wrench.grouper import GROUPERS, BaseGrouper
from wrench.harvester import HARVESTERS, BaseHarvester
from wrench.metadataenricher import METADATA_ENRICHERS, BaseMetadataEnricher
from wrench.pipeline.component import Component


def _parse_from_registry(
    config: dict[str, Any], registry: dict[str, type], type_name: str
) -> Any:
    """Parse a config dict using a registry.

    Config format: {"component_name": {params...}}
    Example: {"kinetic": {"resolution": 0.25}}
    """
    if len(config) != 1:
        raise ValueError(
            f"{type_name} config must have exactly one key (the component name), "
            f"got: {list(config.keys())}"
        )
    name, params = next(iter(config.items()))
    if name not in registry:
        raise ValueError(
            f"Unknown {type_name} '{name}'. Available: {list(registry.keys())}"
        )
    return registry[name](**(params or {}))


class HarvesterConfig(BaseModel):
    """Wrapper for harvester configuration."""

    root: Union[BaseHarvester, dict[str, Any]]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("root", mode="before")
    @classmethod
    def validate_root(cls, v: Any) -> Any:
        if isinstance(v, BaseHarvester):
            return v
        if isinstance(v, dict):
            return v
        raise ValueError(f"Expected BaseHarvester or dict, got {type(v)}")

    def parse(self) -> BaseHarvester:
        if isinstance(self.root, BaseHarvester):
            return self.root
        return _parse_from_registry(self.root, HARVESTERS, "harvester")


class GrouperConfig(BaseModel):
    """Wrapper for grouper configuration."""

    root: Union[BaseGrouper, dict[str, Any]]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("root", mode="before")
    @classmethod
    def validate_root(cls, v: Any) -> Any:
        if isinstance(v, BaseGrouper):
            return v
        if isinstance(v, dict):
            return v
        raise ValueError(f"Expected BaseGrouper or dict, got {type(v)}")

    def parse(self) -> BaseGrouper:
        if isinstance(self.root, BaseGrouper):
            return self.root
        return _parse_from_registry(self.root, GROUPERS, "grouper")


class MetadataEnricherConfig(BaseModel):
    """Wrapper for metadata enricher configuration."""

    root: Union[BaseMetadataEnricher, dict[str, Any]]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("root", mode="before")
    @classmethod
    def validate_root(cls, v: Any) -> Any:
        if isinstance(v, BaseMetadataEnricher):
            return v
        if isinstance(v, dict):
            return v
        raise ValueError(f"Expected BaseMetadataEnricher or dict, got {type(v)}")

    def parse(self) -> BaseMetadataEnricher:
        if isinstance(self.root, BaseMetadataEnricher):
            return self.root
        return _parse_from_registry(self.root, METADATA_ENRICHERS, "metadata_enricher")


class CatalogerConfig(BaseModel):
    """Wrapper for cataloger configuration."""

    root: Union[BaseCataloger, dict[str, Any]]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("root", mode="before")
    @classmethod
    def validate_root(cls, v: Any) -> Any:
        if isinstance(v, BaseCataloger):
            return v
        if isinstance(v, dict):
            return v
        raise ValueError(f"Expected BaseCataloger or dict, got {type(v)}")

    def parse(self) -> BaseCataloger:
        if isinstance(self.root, BaseCataloger):
            return self.root
        return _parse_from_registry(self.root, CATALOGERS, "cataloger")


class ComponentConfig(BaseModel):
    """Wrapper for pipeline component configuration."""

    root: Union[Component, dict[str, Any]]
    run_params: dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("root", mode="before")
    @classmethod
    def validate_root(cls, v: Any) -> Any:
        if isinstance(v, Component):
            return v
        if isinstance(v, dict):
            return v
        raise ValueError(f"Expected Component or dict, got {type(v)}")

    def parse(self) -> Component:
        if isinstance(self.root, Component):
            return self.root
        # Components don't have a registry yet - they use class_ syntax still
        # This can be simplified later if needed
        raise NotImplementedError("Component parsing from dict not yet implemented")

    def get_run_params(self) -> dict[str, Any]:
        return self.run_params
