# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import fsspec
import yaml
from dotenv import load_dotenv
from fsspec.implementations.local import LocalFileSystem


class ConfigReader:
    """Reads config from a file (JSON or YAML format) and returns a dict.

    File format is guessed from the extension. Supported extensions are
    (lower or upper case):

    - .json
    - .yaml, .yml

    Supports environment variable substitution using ${VAR_NAME} syntax.
    """

    def __init__(
        self,
        fs: Optional[fsspec.AbstractFileSystem] = None,
        env_file: Optional[str | Path] = None,
    ) -> None:
        """Initializes a config reader.

        Args:
            fs: Optional filesystem to use for reading files.
            env_file: Optional path to .env file to load.
        """
        self.fs = fs or LocalFileSystem()
        if env_file:
            load_dotenv(env_file)
        else:
            # Try common locations
            for location in [".env", "test_script/.env", Path.home() / ".wrench.env"]:
                if Path(location).exists():
                    load_dotenv(location)
                    break

    def _resolve_env_vars(self, content: str) -> str:
        """Replace ${VAR_NAME} with environment variable values.

        Args:
            content: String content with potential env var references

        Returns:
            Content with resolved environment variables
        """

        def replace_env_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))

        return re.sub(r"\$\{([^}]+)\}", replace_env_var, content)

    def read_json(self, file_path: str, resolve_env_vars: bool = True) -> Any:
        with self.fs.open(file_path, "r") as f:
            content = f.read()
        if resolve_env_vars:
            content = self._resolve_env_vars(content)
        return json.loads(content)

    def read_yaml(self, file_path: str, resolve_env_vars: bool = True) -> Any:
        with self.fs.open(file_path, "r") as f:
            content = f.read()
        if resolve_env_vars:
            content = self._resolve_env_vars(content)
        return yaml.safe_load(content)

    def _guess_format_and_read(
        self, file_path: str, resolve_env_vars: bool = True
    ) -> dict[str, Any]:
        p = Path(file_path)
        extension = p.suffix.lower()
        # Note: .suffix returns an empty string if Path has no extension
        # if not returning a dict, parsing will fail later on
        if extension in [".json"]:
            return self.read_json(file_path, resolve_env_vars)  # type: ignore[no-any-return]
        if extension in [".yaml", ".yml"]:
            return self.read_yaml(file_path, resolve_env_vars)  # type: ignore[no-any-return]
        raise ValueError(f"Unsupported extension: {extension}")

    def read(self, file_path: str, resolve_env_vars: bool = True) -> dict[str, Any]:
        """Read a configuration file.

        Args:
            file_path: Path to the configuration file.
            resolve_env_vars: Whether to resolve ${VAR} environment variables.

        Returns:
            Parsed configuration dictionary.
        """
        data = self._guess_format_and_read(file_path, resolve_env_vars)
        return data
