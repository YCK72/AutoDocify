import os
from typing import List

from pathlib import Path

def scan_python_files(file_path):
    """
    Check if the given file is a valid, non-test, non-migration Python file.
    """
    path = Path(file_path)
    name = path.name.lower()
    return (
        path.suffix == ".py"
        and "__init__" not in name
        and "test" not in name
        and "migration" not in name
    )

