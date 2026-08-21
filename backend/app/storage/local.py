import asyncio
from pathlib import Path

from app.storage.base import ObjectNotFoundError, StorageError, StoredObject


class LocalObjectStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _resolve(self, key: str, *, allow_absolute: bool = True) -> Path:
        candidate = Path(key)
        if candidate.is_absolute():
            if not allow_absolute:
                raise StorageError("Object keys must be relative.")
            path = candidate.resolve()
        else:
            path = (self._root / candidate).resolve()
        if not path.is_relative_to(self._root):
            raise StorageError("Object key escapes the configured storage root.")
        return path

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        del content_type
        path = self._resolve(key, allow_absolute=False)
        try:
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, data)
        except OSError as exc:
            raise StorageError("Unable to write the object.") from exc

    async def get(self, key: str) -> StoredObject:
        path = self._resolve(key)
        try:
            data = await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise ObjectNotFoundError("Object not found.") from exc
        except OSError as exc:
            raise StorageError("Unable to read the object.") from exc
        return StoredObject(data=data, content_type="application/pdf")

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError as exc:
            raise StorageError("Unable to delete the object.") from exc
