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
from wrench.pipeline.config.param_resolver import (
    ParamConfig,
    ParamToResolveConfig,
    _convert_dict_to_param_config,
)

T = TypeVar("T")
"""Generic type to help mypy with the parse method when we know the exact
expected return type.
"""


def issubclass_safe(
    cls: type[object], class_or_tuple: Union[type[object], tuple[type[object]]]
) -> bool:
    """Checks if subclass is safe."""
    if isinstance(class_or_tuple, tuple):
        return any(issubclass_safe(cls, base) for base in class_or_tuple)

    if issubclass(cls, class_or_tuple):
        return True

    # Handle case where module was reloaded
    cls_module = importlib.import_module(cls.__module__)
    # Get the latest version of the base class from the module
    latest_base = getattr(cls_module, class_or_tuple.__name__, None)
    latest_base = cast(Union[tuple[type[object], ...], type[object]], latest_base)
    if issubclass(cls, latest_base):
        return True

    return False


class ObjectConfig(BaseModel, Generic[T]):
    """Config of an object from a class name and its constructor parameters.

    Provides methods to get a class from a string and resolve a parameter defined by
    a dict with a 'resolver_' key.
    """

    class_: str | None = Field(default=None, validate_default=True)
    """Path to class to be instantiated."""
    params_: dict[str, ParamConfig] = {}
    """Initialization parameters."""

    DEFAULT_MODULE: ClassVar[str] = "."
    """Default module to import the class from."""
    INTERFACE: ClassVar[type] = object
    """Constraint on the class (must be a subclass of)."""
    REQUIRED_PARAMS: ClassVar[list[str]] = []
    """List of required parameters for this object constructor."""

    _global_data: dict[str, Any] = PrivateAttr(default_factory=dict)
    """Additional parameter ignored by all Pydantic model_* methods."""
    _logger = PrivateAttr()

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._logger = logger.getChild(self.__class__.__name__)

    def resolve_param(self, param: ParamConfig) -> Any:
        """Finds the parameter value from its definition."""
        if not isinstance(param, ParamToResolveConfig):
            # some parameters do not have to be resolved, real
            # values are already provided
            return param
        return param.resolve(self._global_data)

    def resolve_params(self, params: dict[str, ParamConfig]) -> dict[str, Any]:
        """Resolve all parameters recursively."""
        result = {}
        for param_name, param in params.items():
            if isinstance(param, dict):
                # Recursively resolve nested dictionaries
                result[param_name] = self._resolve_nested_param(param)
            else:
                result[param_name] = self.resolve_param(param)
        return result

    def _resolve_nested_param(self, param_dict: dict[str, Any]) -> dict[str, Any]:
        """Recursively resolve parameters in nested dictionaries."""
        result = {}
        for key, value in param_dict.items():
            if isinstance(value, dict):
                # This nested dict should now contain properly converted ParamConfig
                result[key] = self._resolve_nested_param(value)
            else:
                # This could be a ParamConfig object or regular value
                result[key] = self.resolve_param(value)
        return result

    @field_validator("params_")
    @classmethod
    def validate_params(cls, params_: dict[str, Any]) -> dict[str, Any]:
        """
        Make sure all required parameters are provided.

        Recursively converts nested parameters
        """
        for p in cls.REQUIRED_PARAMS:
            if p not in params_:
                raise ValueError(f"Missing parameter {p}")

        # Recursively convert nested dictionaries with resolver_ keys to ParamConfig
        converted_params = {}
        for key, value in params_.items():
            converted_params[key] = _convert_dict_to_param_config(value)

        return converted_params

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
        # splits class path from module path
        *modules, class_name = class_path.rsplit(".", 1)
        module_name = modules[0] if modules else optional_module

        if module_name is None:
            raise ValueError("Must specify a module to import class from")

        try:
            module = importlib.import_module(module_name)
            # get class_name from the module if available
            klass = getattr(module, class_name)
        except (ImportError, AttributeError):
            if optional_module and module_name != optional_module:
                full_klass_path = optional_module + "." + class_path
                return cls._get_class(full_klass_path)
            raise ValueError(f"Could not find {class_name} in {module_name}")

        return cast(type, klass)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> T:
        """Import `class_`, resolve `params_` and instantiate object."""
        self._global_data = resolved_data or {}
        self._logger.debug(f"OBJECT_CONFIG: parsing {self} using {resolved_data}")

        if self.class_ is None:
            raise ValueError(f"`class_` is required to parse object {self}")
        klass = self._get_class(self.class_, self.get_module())
        if not issubclass_safe(klass, self.get_interface()):
            raise ValueError(
                f"""Invalid class '{klass}'. Expected a subclass of
                    '{self.get_interface()}'"""
            )
        params = self.resolve_params(self.params_)
        try:
            obj = klass(**params)
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


def _validate_harvester_type(
    v: Any,
) -> Union[BaseHarvester, HarvesterConfig]:
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
            # Allow direct field initialization
            super().__init__(root=data, **{})
        else:
            super().__init__(root=root, **data)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> BaseHarvester:
        if isinstance(self.root, BaseHarvester):
            return self.root
        return self.root.parse(resolved_data)


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

    def parse(self, resolved_data: dict[str, Any] | None = None) -> BaseGrouper:
        if isinstance(self.root, BaseGrouper):
            return self.root
        return self.root.parse(resolved_data)


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

    def parse(
        self, resolved_data: dict[str, Any] | None = None
    ) -> BaseMetadataEnricher:
        if isinstance(self.root, BaseMetadataEnricher):
            return self.root
        return self.root.parse(resolved_data)


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

    def parse(self, resolved_data: dict[str, Any] | None = None) -> BaseCataloger:
        if isinstance(self.root, BaseCataloger):
            return self.root
        return self.root.parse(resolved_data)


class ComponentConfig(ObjectConfig[Component]):
    """A config model for all components.

    In addition to the object config, components can have pre-defined parameters
    that will be passed to the `run` method, ie `run_params_`.
    """

    run_params_: dict[str, ParamConfig] = {}

    DEFAULT_MODULE = "wrench.components"
    INTERFACE = Component

    def get_run_params(self, resolved_data: dict[str, Any]) -> dict[str, Any]:
        self._global_data = resolved_data
        return self.resolve_params(self.run_params_)


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

    def parse(self, resolved_data: dict[str, Any] | None = None) -> Component:
        if isinstance(self.root, Component):
            return self.root
        return self.root.parse(resolved_data)

    def get_run_params(self, resolved_data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(self.root, Component):
            return {}
        return self.root.get_run_params(resolved_data)
