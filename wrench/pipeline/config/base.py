# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

from typing import Any

from pydantic import BaseModel, PrivateAttr

from wrench.pipeline.config.param_resolver import ParamConfig, ParamToResolveConfig


class AbstractConfig(BaseModel):
    """Base class for all configs.

    Provides methods to get a class from a string and resolve a parameter defined by
    a dict with a 'resolver_' key.

    Each subclass must implement a 'parse' method that returns the relevant object.
    """

    _global_data: dict[str, Any] = PrivateAttr({})
    """Additional parameter ignored by all Pydantic model_* methods."""

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

    def parse(self, resolved_data: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError()
