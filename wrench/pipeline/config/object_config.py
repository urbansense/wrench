# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

from __future__ import annotations

import importlib
from typing import (
    Annotated,
    Any,
    ClassVar,
    Generic,
    Optional,
    TypeVar,
    Union,
    cast,
)

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
)

from wrench.cataloger import BaseCataloger
from wrench.grouper import BaseGrouper
from wrench.harvester import BaseHarvester
from wrench.log import logger
from wrench.metadataenricher import BaseMetadataEnricher
from wrench.pipeline.component import Component

T = TypeVar("T")


class ObjectConfig(BaseModel, Generic[T]):
    """Config of an object from a class name and its constructor parameters."""

    class_: str | None = Field(default=None, validate_default=True)
    """Path to class to be instantiated."""
    params_: dict[str, Any] = {}
    """Initialization parameters."""

    DEFAULT_MODULE: ClassVar[str] = "."
    """Default module to import the class from."""
    INTERFACE: ClassVar[type] = object
    """Constraint on the class (must be a subclass of)."""
    REQUIRED_PARAMS: ClassVar[list[str]] = []
    """List of required parameters for this object constructor."""

    _logger = PrivateAttr()

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._logger = logger.getChild(self.__class__.__name__)

    @field_validator("params_")
    @classmethod
    def validate_params(cls, params_: dict[str, Any]) -> dict[str, Any]:
        """Make sure all required parameters are provided."""
        for p in cls.REQUIRED_PARAMS:
            if p not in params_:
                raise ValueError(f"Missing parameter {p}")
        return params_

    def get_module(self) -> str:
        return self.DEFAULT_MODULE

    def get_interface(self) -> type:
        return self.INTERFACE

    @classmethod
    def _get_class(cls, class_path: str, optional_module: Optional[str] = None) -> type:
        """Get class from string and an optional module.

        Will first try to import the class from `class_path` alone. If it results in an
        ImportError, will try to import from `f'{optional_module}.{class_path}'`

        Args:
            class_path (str): Class path with format 'my_module.MyClass'.
            optional_module (Optional[str]): Optional module path. Used to provide a
            default path for some known objects and simplify the notation.

        Raises:
            ValueError: if the class can't be imported, even using the optional module.
        """
        *modules, class_name = class_path.rsplit(".", 1)
        module_name = modules[0] if modules else optional_module

        if module_name is None:
            raise ValueError("Must specify a module to import class from")

        try:
            module = importlib.import_module(module_name)
            klass = getattr(module, class_name)
        except (ImportError, AttributeError):
            if optional_module and module_name != optional_module:
                full_klass_path = optional_module + "." + class_path
                return cls._get_class(full_klass_path)
            raise ValueError(f"Could not find {class_name} in {module_name}")

        return cast(type, klass)

    def parse(self) -> T:
        """Import `class_` and instantiate object with `params_`."""
        self._logger.debug(f"OBJECT_CONFIG: parsing {self}")

        if self.class_ is None:
            raise ValueError(f"`class_` is required to parse object {self}")
        klass = self._get_class(self.class_, self.get_module())
        if not issubclass(klass, self.get_interface()):
            raise ValueError(
                f"Invalid class '{klass}'. Expected a subclass \
                    of '{self.get_interface()}'"
            )
        try:
            obj = klass(**self.params_)
        except TypeError as e:
            self._logger.error(
                "failed to instantiate object due to improperly configured parameters"
            )
            raise e
        return cast(T, obj)


class HarvesterConfig(ObjectConfig[BaseHarvester]):
    """Configuration for any Harvester object.

    By default, will try to import from `wrench.harvester`.
    """

    DEFAULT_MODULE = "wrench.harvester"
    INTERFACE = BaseHarvester


def _validate_harvester_type(v: Any) -> Union[BaseHarvester, HarvesterConfig]:
    """Validator for HarvesterType that handles both instances and config dicts."""
    if isinstance(v, BaseHarvester):
        return v
    if isinstance(v, HarvesterConfig):
        return v
    if isinstance(v, dict):
        return HarvesterConfig.model_validate(v)
    return v


class HarvesterType(BaseModel):
    """A model to wrap BaseHarvester and HarvesterConfig objects.

    The `parse` method always returns an object inheriting from BaseHarvester.
    """

    root: Annotated[
        Union[BaseHarvester, HarvesterConfig], BeforeValidator(_validate_harvester_type)
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, root: Any = None, **data: Any) -> None:
        if root is not None:
            super().__init__(root=root, **data)
        elif data:
            super().__init__(root=data, **{})
        else:
            super().__init__(root=root, **data)

    def parse(self) -> BaseHarvester:
        if isinstance(self.root, BaseHarvester):
            return self.root
        return self.root.parse()


class GrouperConfig(ObjectConfig[BaseGrouper]):
    """Configuration for any Grouper object.

    By default, will try to import from `wrench.grouper`.
    """

    DEFAULT_MODULE = "wrench.grouper"
    INTERFACE = BaseGrouper


def _validate_grouper_type(v: Any) -> Union[BaseGrouper, GrouperConfig]:
    """Validator for GrouperType that handles both instances and config dicts."""
    if isinstance(v, BaseGrouper):
        return v
    if isinstance(v, GrouperConfig):
        return v
    if isinstance(v, dict):
        return GrouperConfig.model_validate(v)
    return v


class GrouperType(BaseModel):
    """A model to wrap BaseGrouper and GrouperConfig objects.

    The `parse` method always returns an object inheriting from BaseGrouper.
    """

    root: Annotated[
        Union[BaseGrouper, GrouperConfig], BeforeValidator(_validate_grouper_type)
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, root: Any = None, **data: Any) -> None:
        if root is not None:
            super().__init__(root=root, **data)
        elif data:
            super().__init__(root=data, **{})
        else:
            super().__init__(root=root, **data)

    def parse(self) -> BaseGrouper:
        if isinstance(self.root, BaseGrouper):
            return self.root
        return self.root.parse()


class MetadataEnricherConfig(ObjectConfig[BaseMetadataEnricher]):
    """Configuration for any BaseMetadataEnricher object.

    By default, will try to import from `wrench.metadataenricher`.
    """

    DEFAULT_MODULE = "wrench.metadataenricher"
    INTERFACE = BaseMetadataEnricher


def _validate_metadataenricher_type(
    v: Any,
) -> Union[BaseMetadataEnricher, MetadataEnricherConfig]:
    """Validator for MetadataEnricherType."""
    if isinstance(v, BaseMetadataEnricher):
        return v
    if isinstance(v, MetadataEnricherConfig):
        return v
    if isinstance(v, dict):
        return MetadataEnricherConfig.model_validate(v)
    return v


class MetadataEnricherType(BaseModel):
    """A model to wrap BaseMetadataEnricher and MetadataEnricherConfig objects.

    The `parse` method always returns an object inheriting from BaseMetadataEnricher.
    """

    root: Annotated[
        Union[BaseMetadataEnricher, MetadataEnricherConfig],
        BeforeValidator(_validate_metadataenricher_type),
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, root: Any = None, **data: Any) -> None:
        if root is not None:
            super().__init__(root=root, **data)
        elif data:
            super().__init__(root=data, **{})
        else:
            super().__init__(root=root, **data)

    def parse(self) -> BaseMetadataEnricher:
        if isinstance(self.root, BaseMetadataEnricher):
            return self.root
        return self.root.parse()


class CatalogerConfig(ObjectConfig[BaseCataloger]):
    """Configuration for any BaseCataloger object.

    By default, will try to import from `wrench.cataloger`.
    """

    DEFAULT_MODULE = "wrench.cataloger"
    INTERFACE = BaseCataloger


def _validate_cataloger_type(v: Any) -> Union[BaseCataloger, CatalogerConfig]:
    """Validator for CatalogerType."""
    if isinstance(v, BaseCataloger):
        return v
    if isinstance(v, CatalogerConfig):
        return v
    if isinstance(v, dict):
        return CatalogerConfig.model_validate(v)
    return v


class CatalogerType(BaseModel):
    """A model to wrap BaseCataloger and CatalogerConfig objects.

    The `parse` method always returns an object inheriting from BaseCataloger.
    """

    root: Annotated[
        Union[BaseCataloger, CatalogerConfig], BeforeValidator(_validate_cataloger_type)
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, root: Any = None, **data: Any) -> None:
        if root is not None:
            super().__init__(root=root, **data)
        elif data:
            super().__init__(root=data, **{})
        else:
            super().__init__(root=root, **data)

    def parse(self) -> BaseCataloger:
        if isinstance(self.root, BaseCataloger):
            return self.root
        return self.root.parse()


class ComponentConfig(ObjectConfig[Component]):
    """A config model for all components.

    In addition to the object config, components can have pre-defined parameters
    that will be passed to the `run` method, ie `run_params_`.
    """

    run_params_: dict[str, Any] = {}

    DEFAULT_MODULE = "wrench.components"
    INTERFACE = Component

    def get_run_params(self) -> dict[str, Any]:
        return self.run_params_


def _validate_component_type(v: Any) -> Union[Component, ComponentConfig]:
    """Validator for ComponentType."""
    if isinstance(v, Component):
        return v
    if isinstance(v, ComponentConfig):
        return v
    if isinstance(v, dict):
        return ComponentConfig.model_validate(v)
    return v


class ComponentType(BaseModel):
    """A model to wrap Component and ComponentConfig objects."""

    root: Annotated[
        Union[Component, ComponentConfig], BeforeValidator(_validate_component_type)
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, root: Any = None, **data: Any) -> None:
        if root is not None:
            super().__init__(root=root, **data)
        elif data:
            super().__init__(root=data, **{})
        else:
            super().__init__(root=root, **data)

    def parse(self) -> Component:
        if isinstance(self.root, Component):
            return self.root
        return self.root.parse()

    def get_run_params(self) -> dict[str, Any]:
        if isinstance(self.root, Component):
            return {}
        return self.root.get_run_params()
