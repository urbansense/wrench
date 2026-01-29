# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

import enum
from typing import Any, ClassVar, Literal, Union

from pydantic import BaseModel


class ParamResolverEnum(str, enum.Enum):
    CONFIG_KEY = "CONFIG_KEY"


class ParamToResolveConfig(BaseModel):
    def resolve(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError


class ParamFromKeyConfig(ParamToResolveConfig):
    """Resolver for cross-referencing values from other parts of the config."""

    resolver_: Literal[ParamResolverEnum.CONFIG_KEY] = ParamResolverEnum.CONFIG_KEY
    key_: str

    KEY_SEP: ClassVar[str] = "."

    def resolve(self, data: dict[str, Any]) -> Any:
        d = data
        for k in self.key_.split(self.KEY_SEP):
            if not isinstance(d, dict):
                raise AttributeError(f"Path component '{k}' refers to a non-dict value")
            d = d[k]
        return d


# Union type for resolver validation
ResolverConfig = ParamFromKeyConfig


def _convert_dict_to_param_config(value: Any) -> Any:
    """Recursively convert dictionaries with resolver_ keys to ParamConfig objects."""
    if isinstance(value, dict):
        # Check if this dict has a resolver_ key (it's a param config)
        if "resolver_" in value:
            try:
                # Use Pydantic's Union validation to convert automatically
                from pydantic import TypeAdapter

                adapter = TypeAdapter(ResolverConfig)
                return adapter.validate_python(value)
            except Exception:
                # If validation fails, keep as dict
                return value
        else:
            # Regular dict, recursively process its values
            return {k: _convert_dict_to_param_config(v) for k, v in value.items()}
    elif isinstance(value, list):
        # Process lists recursively too
        return [_convert_dict_to_param_config(item) for item in value]
    else:
        # Regular value, return as-is
        return value


ParamConfig = Union[
    float,
    str,
    ParamFromKeyConfig,
    dict[str, Any],
]
