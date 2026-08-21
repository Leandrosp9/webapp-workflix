from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.storage.base import ObjectStorage
from app.storage.local import LocalObjectStorage
from app.storage.s3 import S3ObjectStorage


@lru_cache
def _build_storage(
    provider: str,
    local_root: str,
    bucket: str,
    region: str,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    force_path_style: bool,
    server_side_encryption: str,
    kms_key_id: str,
) -> ObjectStorage:
    if provider in {"s3", "r2"}:
        return S3ObjectStorage(
            bucket=bucket,
            region=region,
            endpoint_url=endpoint_url or None,
            access_key_id=access_key_id or None,
            secret_access_key=secret_access_key or None,
            force_path_style=force_path_style,
            server_side_encryption=server_side_encryption or None,
            kms_key_id=kms_key_id or None,
        )
    return LocalObjectStorage(Path(local_root))


def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    return _build_storage(
        settings.file_storage_provider,
        str(settings.upload_directory.resolve()),
        settings.s3_bucket or "",
        settings.s3_region,
        settings.s3_endpoint_url or "",
        settings.s3_access_key_id.get_secret_value() if settings.s3_access_key_id else "",
        settings.s3_secret_access_key.get_secret_value() if settings.s3_secret_access_key else "",
        settings.s3_force_path_style,
        settings.s3_server_side_encryption or "",
        settings.s3_kms_key_id or "",
    )
