"""Object storage protocol and local filesystem adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStorage(Protocol):
    async def put_pdf(self, *, object_key: str, data: bytes, content_type: str) -> str: ...

    async def get_pdf(self, *, object_key: str) -> bytes: ...

    async def delete_object(self, *, object_key: str) -> None: ...


class LocalObjectStorage:
    """Stores PDF bytes under a local directory (development / Task 2 default)."""

    provider_name = "local"

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, object_key: str) -> Path:
        # Object keys are server-generated; reject path traversal defensively.
        safe = object_key.replace("\\", "/").lstrip("/")
        if ".." in Path(safe).parts:
            raise ValueError("Invalid object key.")
        path = (self._root / safe).resolve()
        if not str(path).startswith(str(self._root.resolve())):
            raise ValueError("Invalid object key.")
        return path

    async def put_pdf(self, *, object_key: str, data: bytes, content_type: str) -> str:
        _ = content_type
        path = self._path_for(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return object_key

    async def get_pdf(self, *, object_key: str) -> bytes:
        path = self._path_for(object_key)
        if not path.is_file():
            raise FileNotFoundError(object_key)
        return path.read_bytes()

    async def delete_object(self, *, object_key: str) -> None:
        path = self._path_for(object_key)
        if path.exists():
            path.unlink()
