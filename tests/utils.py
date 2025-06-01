import inspect
import json
import os
from pathlib import Path
from typing import Any


def get_caller() -> Path:
    caller_frame = inspect.stack()[1]
    caller_file_path = Path(caller_frame.filename)

    return caller_file_path


def load_json(filename: str) -> list[dict[str, Any]]:
    caller_file_path = get_caller()

    # Use the directory of the calling file
    data_dir = caller_file_path.parent / "testdata"
    with open(os.path.join(data_dir, filename), "r") as f:
        data = json.load(f)
    return data
