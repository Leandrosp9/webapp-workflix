import base64
import json
import os
from collections.abc import MutableMapping
from typing import Any, Protocol

import boto3

ALLOWED_SECRET_KEYS = frozenset(
    {
        "DATABASE_URL",
        "JWT_SECRET",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "REDIS_URL",
    }
)


class ManagedSecretsError(RuntimeError):
    """Raised when managed configuration cannot be loaded safely."""


class SecretsLoader(Protocol):
    def load(self) -> dict[str, str]: ...


class AWSSecretsManagerLoader:
    def __init__(
        self,
        *,
        secret_id: str,
        region: str,
        endpoint_url: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._secret_id = secret_id
        self._client = client or boto3.client(
            "secretsmanager", region_name=region, endpoint_url=endpoint_url
        )

    def load(self) -> dict[str, str]:
        try:
            response = self._client.get_secret_value(SecretId=self._secret_id)
        except Exception as exc:
            raise ManagedSecretsError("Unable to retrieve the configured managed secret.") from exc

        raw_secret = response.get("SecretString")
        if raw_secret is None and (binary_secret := response.get("SecretBinary")) is not None:
            if isinstance(binary_secret, str):
                raw_secret = base64.b64decode(binary_secret).decode("utf-8")
            else:
                raw_secret = bytes(binary_secret).decode("utf-8")
        if not raw_secret:
            raise ManagedSecretsError("The configured managed secret is empty.")

        try:
            payload = json.loads(raw_secret)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ManagedSecretsError("The managed secret must contain a JSON object.") from exc
        if not isinstance(payload, dict):
            raise ManagedSecretsError("The managed secret must contain a JSON object.")

        values: dict[str, str] = {}
        for key, value in payload.items():
            normalized_key = str(key).upper()
            if normalized_key in ALLOWED_SECRET_KEYS and isinstance(value, str) and value:
                values[normalized_key] = value
        return values


def load_managed_secrets(
    environ: MutableMapping[str, str] | None = None,
    *,
    loader: SecretsLoader | None = None,
) -> None:
    target = environ if environ is not None else os.environ
    provider = target.get("SECRETS_MANAGER_PROVIDER", "env").strip().lower()
    if provider == "env":
        return
    if provider != "aws":
        raise ManagedSecretsError(f"Unsupported secrets manager provider: {provider}")

    if loader is None:
        secret_id = target.get("AWS_SECRET_ID", "").strip()
        if not secret_id:
            raise ManagedSecretsError("AWS_SECRET_ID is required for AWS Secrets Manager.")
        loader = AWSSecretsManagerLoader(
            secret_id=secret_id,
            region=target.get("AWS_REGION", "us-east-1"),
            endpoint_url=target.get("AWS_SECRETS_ENDPOINT_URL") or None,
        )

    for key, value in loader.load().items():
        if key in ALLOWED_SECRET_KEYS and not target.get(key):
            target[key] = value
