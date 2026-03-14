import json

import pytest
import yaml

from wrench.pipeline.config.config_reader import ConfigReader


@pytest.fixture()
def reader():
    return ConfigReader()


class TestReadJson:
    def test_read_json_file(self, tmp_path, reader):
        config = {"name": "test", "value": 42}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read_json(str(f))
        assert result == config

    def test_read_json_nested(self, tmp_path, reader):
        config = {"pipeline": {"components": [{"name": "a"}, {"name": "b"}]}}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read_json(str(f))
        assert result["pipeline"]["components"][0]["name"] == "a"


class TestReadYaml:
    def test_read_yaml_file(self, tmp_path, reader):
        config = {"name": "test", "value": 42}
        f = tmp_path / "config.yaml"
        f.write_text(yaml.dump(config))
        result = reader.read_yaml(str(f))
        assert result == config

    def test_read_yml_extension(self, tmp_path, reader):
        config = {"key": "value"}
        f = tmp_path / "config.yml"
        f.write_text(yaml.dump(config))
        result = reader.read_yaml(str(f))
        assert result == config


class TestGuessFormatAndRead:
    def test_auto_detect_json(self, tmp_path, reader):
        config = {"format": "json"}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read(str(f))
        assert result == config

    def test_auto_detect_yaml(self, tmp_path, reader):
        config = {"format": "yaml"}
        f = tmp_path / "config.yaml"
        f.write_text(yaml.dump(config))
        result = reader.read(str(f))
        assert result == config

    def test_auto_detect_yml(self, tmp_path, reader):
        config = {"format": "yml"}
        f = tmp_path / "config.yml"
        f.write_text(yaml.dump(config))
        result = reader.read(str(f))
        assert result == config

    def test_unsupported_extension_raises(self, tmp_path, reader):
        f = tmp_path / "config.toml"
        f.write_text("key = 'value'")
        with pytest.raises(ValueError, match="Unsupported extension"):
            reader.read(str(f))


class TestEnvVarSubstitution:
    def test_env_var_resolved(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "secret-123")
        reader = ConfigReader()
        config = {"api_key": "${TEST_API_KEY}"}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read_json(str(f))
        assert result["api_key"] == "secret-123"

    def test_env_var_not_set_keeps_original(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR_XYZ", raising=False)
        reader = ConfigReader()
        config = {"key": "${NONEXISTENT_VAR_XYZ}"}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read_json(str(f))
        assert result["key"] == "${NONEXISTENT_VAR_XYZ}"

    def test_multiple_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "5432")
        reader = ConfigReader()
        config = {"url": "${HOST}:${PORT}"}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read_json(str(f))
        assert result["url"] == "localhost:5432"

    def test_env_var_in_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DB_NAME", "mydb")
        reader = ConfigReader()
        f = tmp_path / "config.yaml"
        f.write_text("database: ${DB_NAME}")
        result = reader.read_yaml(str(f))
        assert result["database"] == "mydb"

    def test_resolve_env_vars_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "resolved")
        reader = ConfigReader()
        config = {"key": "${TEST_VAR}"}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read_json(str(f), resolve_env_vars=False)
        assert result["key"] == "${TEST_VAR}"

    def test_env_var_with_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FROM_FILE=file-value\n")
        reader = ConfigReader(env_file=str(env_file))
        config = {"key": "${FROM_FILE}"}
        f = tmp_path / "config.json"
        f.write_text(json.dumps(config))
        result = reader.read_json(str(f))
        assert result["key"] == "file-value"


class TestResolveEnvVarsMethod:
    def test_no_vars_returns_unchanged(self, reader):
        assert reader._resolve_env_vars("plain text") == "plain text"

    def test_single_var(self, monkeypatch, reader):
        monkeypatch.setenv("FOO", "bar")
        assert reader._resolve_env_vars("${FOO}") == "bar"

    def test_var_embedded_in_string(self, monkeypatch, reader):
        monkeypatch.setenv("NAME", "world")
        result = reader._resolve_env_vars("hello ${NAME}!")
        assert result == "hello world!"
