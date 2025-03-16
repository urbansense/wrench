import os
from unittest.mock import patch

import pytest

from wrench.pipeline.config.param_resolver import (
    ParamFromEnvConfig,
    ParamFromKeyConfig,
    ParamResolverEnum,
)


def test_param_from_env_config():
    """Test resolving parameters from environment variables."""
    with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        param = ParamFromEnvConfig(var_="TEST_VAR")
        assert param.resolver_ == ParamResolverEnum.ENV
        result = param.resolve({})
        assert result == "test_value"


def test_param_from_env_config_missing():
    """Test resolving parameters from non-existent environment variables."""
    param = ParamFromEnvConfig(var_="NONEXISTENT_VAR")
    result = param.resolve({})
    assert result is None


def test_param_from_key_config():
    """Test resolving parameters from configuration keys."""
    data = {"level1": {"level2": {"level3": "value"}}}
    param = ParamFromKeyConfig(key_="level1.level2.level3")
    assert param.resolver_ == ParamResolverEnum.CONFIG_KEY
    result = param.resolve(data)
    assert result == "value"


def test_param_from_key_config_nested():
    """Test resolving deeply nested parameters."""
    data = {"a": {"b": {"c": {"d": {"e": "nested_value"}}}}}
    param = ParamFromKeyConfig(key_="a.b.c.d.e")
    result = param.resolve(data)
    assert result == "nested_value"


def test_param_from_key_config_missing_key():
    """Test resolving parameters with missing keys."""
    data = {"level1": {"level2": {}}}
    param = ParamFromKeyConfig(key_="level1.level2.level3")
    with pytest.raises(KeyError):
        param.resolve(data)


def test_param_from_key_config_invalid_path():
    """Test resolving parameters with invalid path types."""
    data = {"level1": "not_a_dict"}
    param = ParamFromKeyConfig(key_="level1.level2")
    with pytest.raises(AttributeError):
        param.resolve(data)
