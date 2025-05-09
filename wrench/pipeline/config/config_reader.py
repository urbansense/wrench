import json
from pathlib import Path
from typing import Any, Optional

import fsspec
import yaml
from fsspec.implementations.local import LocalFileSystem


class ConfigReader:
    """Reads config from a file (JSON or YAML format) and returns a dict.

    File format is guessed from the extension. Supported extensions are
    (lower or upper case):

    - .json
    - .yaml, .yml

    """

    def __init__(self, fs: Optional[fsspec.AbstractFileSystem] = None) -> None:
        """Initializes a config reader."""
        self.fs = fs or LocalFileSystem()

    def read_json(self, file_path: str) -> Any:
        with self.fs.open(file_path, "r") as f:
            return json.load(f)

    def read_yaml(self, file_path: str) -> Any:
        with self.fs.open(file_path, "r") as f:
            return yaml.safe_load(f)

    def _guess_format_and_read(self, file_path: str) -> dict[str, Any]:
        p = Path(file_path)
        extension = p.suffix.lower()
        # Note: .suffix returns an empty string if Path has no extension
        # if not returning a dict, parsing will fail later on
        if extension in [".json"]:
            return self.read_json(file_path)  # type: ignore[no-any-return]
        if extension in [".yaml", ".yml"]:
            return self.read_yaml(file_path)  # type: ignore[no-any-return]
        raise ValueError(f"Unsupported extension: {extension}")

    def read(self, file_path: str) -> dict[str, Any]:
        data = self._guess_format_and_read(file_path)
        return data
