from dataclasses import dataclass
from typing import Protocol


class StorageError(RuntimeError):
    """Raised when object storage cannot complete an operation."""


class ObjectNotFoundError(StorageError):
    """Raised when an object key does not exist."""


@dataclass(frozen=True, slots=True)
class StoredObject:
    data: bytes
    content_type: str


class ObjectStorage(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    async def get(self, key: str) -> StoredObject: ...

    async def delete(self, key: str) -> None: ...
