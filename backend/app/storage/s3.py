import asyncio
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.storage.base import ObjectNotFoundError, StorageError, StoredObject


class S3ObjectStorage:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        force_path_style: bool = False,
        server_side_encryption: str | None = None,
        kms_key_id: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._bucket = bucket
        self._server_side_encryption = server_side_encryption
        self._kms_key_id = kms_key_id
        self._client = client or boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(s3={"addressing_style": "path" if force_path_style else "auto"}),
        )

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        if self._server_side_encryption:
            kwargs["ServerSideEncryption"] = self._server_side_encryption
        if self._kms_key_id:
            kwargs["SSEKMSKeyId"] = self._kms_key_id
        try:
            await asyncio.to_thread(self._client.put_object, **kwargs)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to write the object.") from exc

    async def get(self, key: str) -> StoredObject:
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._bucket, Key=key
            )
            data = await asyncio.to_thread(response["Body"].read)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                raise ObjectNotFoundError("Object not found.") from exc
            raise StorageError("Unable to read the object.") from exc
        except (BotoCoreError, KeyError, OSError) as exc:
            raise StorageError("Unable to read the object.") from exc
        return StoredObject(
            data=data,
            content_type=str(response.get("ContentType") or "application/octet-stream"),
        )

    async def delete(self, key: str) -> None:
        try:
            await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to delete the object.") from exc
