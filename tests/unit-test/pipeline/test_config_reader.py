import json
import os
import tempfile

import pytest
import yaml

from wrench.pipeline.config.config_reader import ConfigReader


@pytest.fixture
def config_reader():
    return ConfigReader()


@pytest.fixture
def json_data():
    return {"name": "test", "value": 123}


@pytest.fixture
def yaml_data():
    return {"name": "test", "nested": {"key": "value"}}


@pytest.fixture
def json_file(json_data):
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(json_data, f)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def yaml_file(yaml_data):
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        yaml.dump(yaml_data, f)
        path = f.name
    yield path
    os.unlink(path)


def test_read_json(config_reader, json_file, json_data):
    """Test reading from a JSON file."""
    result = config_reader.read(json_file)
    assert result == json_data


def test_read_yaml(config_reader, yaml_file, yaml_data):
    """Test reading from a YAML file."""
    result = config_reader.read(yaml_file)
    assert result == yaml_data


def test_read_invalid_extension(config_reader):
    """Test that reading a file with invalid extension raises an error."""
    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        with pytest.raises(ValueError) as excinfo:
            config_reader.read(f.name)
        assert "Unsupported extension" in str(excinfo.value)


def test_read_non_existent_file(config_reader):
    """Test that reading a non-existent file raises an error."""
    with pytest.raises(FileNotFoundError):
        config_reader.read("/path/to/nonexistent/file.json")


def test_read_invalid_json(config_reader):
    """Test that reading invalid JSON raises an error."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(b"invalid json")
        path = f.name

    try:
        with pytest.raises(json.JSONDecodeError):
            config_reader.read(path)
    finally:
        os.unlink(path)


def test_read_invalid_yaml(config_reader):
    """Test that reading invalid YAML raises an error."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"invalid: yaml:\n  - missing")
        path = f.name

    try:
        with pytest.raises(yaml.YAMLError):
            config_reader.read(path)
    finally:
        os.unlink(path)
