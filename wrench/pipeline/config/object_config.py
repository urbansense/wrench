"""Component configuration using registries."""

from __future__ import annotations

from typing import Annotated, Any, Union

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator

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


def _make_parser(registry: dict[str, type], base_type: type, type_name: str):
    """Create a parser function for use with BeforeValidator."""

    def parse(v: Any) -> Any:
        if isinstance(v, base_type):
            return v
        if isinstance(v, dict):
            return _parse_from_registry(v, registry, type_name)
        raise ValueError(f"Expected {base_type.__name__} or dict, got {type(v)}")

    return parse


# Annotated types that auto-parse from dict config
Harvester = Annotated[
    BaseHarvester,
    BeforeValidator(_make_parser(HARVESTERS, BaseHarvester, "harvester")),
]
Grouper = Annotated[
    BaseGrouper,
    BeforeValidator(_make_parser(GROUPERS, BaseGrouper, "grouper")),
]
MetadataEnricher = Annotated[
    BaseMetadataEnricher,
    BeforeValidator(
        _make_parser(METADATA_ENRICHERS, BaseMetadataEnricher, "metadata_enricher")
    ),
]
Cataloger = Annotated[
    BaseCataloger,
    BeforeValidator(_make_parser(CATALOGERS, BaseCataloger, "cataloger")),
]


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
