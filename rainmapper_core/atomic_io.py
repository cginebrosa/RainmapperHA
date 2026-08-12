"""Small atomic file-writing helpers shared by Rainmapper data sources."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_csv_atomic(dataframe, path, **to_csv_kwargs) -> None:
    """Write a CSV beside its target and atomically replace the old file.

    The previous target remains untouched if serialization fails. Keeping the
    temporary file in the same directory also guarantees that the final
    replacement does not cross filesystems.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        dataframe.to_csv(temporary_path, index=False, **to_csv_kwargs)
        with temporary_path.open("rb") as handle:
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
