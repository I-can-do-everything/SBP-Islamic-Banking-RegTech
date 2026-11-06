"""File storage for uploads, canonical Parquet files and generated reports.

The demo keeps files on the local disk of the API container, under one folder
per workspace. Keys look like `<workspace>/<submission>/raw/<file>`, the same
shape an S3 compatible bucket would use, so swapping in object storage later
only means implementing these four functions against that service.

Files under `raw/` are written once and never overwritten (chain of custody).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from daleel.core.config import get_settings
from daleel.core.errors import InvalidInput


def _root() -> Path:
    root = get_settings().data_dir / "store"
    root.mkdir(parents=True, exist_ok=True)
    return root


def path_for(key: str) -> Path:
    """Resolve a key to a local path, refusing anything that escapes the store."""
    root = _root().resolve()
    path = (root / key).resolve()
    if root not in path.parents:
        raise InvalidInput("bad_key", "Invalid storage key.")
    return path


def put_bytes(key: str, data: bytes, immutable: bool = False) -> str:
    path = path_for(key)
    if immutable and path.exists():
        raise InvalidInput("immutable", "This file has already been stored and cannot be replaced.")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)
    return sha256_bytes(data)


def get_bytes(key: str) -> bytes:
    return path_for(key).read_bytes()


def exists(key: str) -> bool:
    return path_for(key).exists()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
