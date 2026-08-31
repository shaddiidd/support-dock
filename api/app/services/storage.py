from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings

MAX_FILE_BYTES = 20 * 1024 * 1024

SUPPORTED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
}

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(Exception):
    pass


def safe_filename(filename: str) -> str:
    name = Path(filename or "").name.strip() or "document"
    cleaned = _UNSAFE_NAME.sub("_", name).strip("._") or "document"
    return cleaned[:180]


def document_title(filename: str) -> str:
    name = Path(filename or "").name
    stem = Path(name).stem.replace("_", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", stem) or "Untitled document"


def content_type_for(filename: str, declared: Optional[str] = None) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[ext]
    if declared and declared in SUPPORTED_EXTENSIONS.values():
        return declared
    return declared or "application/octet-stream"


def is_supported_filename(filename: str) -> bool:
    return Path(filename or "").suffix.lower() in SUPPORTED_EXTENSIONS


def make_object_key(business_id: UUID, document_id: UUID, filename: str) -> str:
    return (
        f"businesses/{business_id}/documents/{document_id}/"
        f"{uuid4().hex[:12]}_{safe_filename(filename)}"
    )


def _client():
    settings = get_settings()
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def require_storage_config() -> None:
    settings = get_settings()
    if not settings.s3_bucket_name.strip():
        raise StorageError("Amazon S3 is not configured. Set S3_BUCKET_NAME in api/.env.")


def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    require_storage_config()
    settings = get_settings()
    try:
        _client().put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
            ContentDisposition=f'attachment; filename="{quote(Path(key).name)}"',
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to store the file in Amazon S3.") from exc


def download_bytes(key: str) -> bytes:
    require_storage_config()
    settings = get_settings()
    try:
        response = _client().get_object(Bucket=settings.s3_bucket_name, Key=key)
        return response["Body"].read()
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to read the file from Amazon S3.") from exc


def delete_object(key: str) -> None:
    if not key:
        return
    require_storage_config()
    settings = get_settings()
    try:
        _client().delete_object(Bucket=settings.s3_bucket_name, Key=key)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to delete the file from Amazon S3.") from exc


def delete_prefix(prefix: str) -> None:
    require_storage_config()
    settings = get_settings()
    client = _client()
    try:
        continuation = None
        while True:
            kwargs = {"Bucket": settings.s3_bucket_name, "Prefix": prefix}
            if continuation:
                kwargs["ContinuationToken"] = continuation
            page = client.list_objects_v2(**kwargs)
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if objects:
                client.delete_objects(
                    Bucket=settings.s3_bucket_name,
                    Delete={"Objects": objects, "Quiet": True},
                )
            if not page.get("IsTruncated"):
                break
            continuation = page.get("NextContinuationToken")
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to delete business files from Amazon S3.") from exc


def presigned_get_url(key: str, filename: str) -> str:
    require_storage_config()
    settings = get_settings()
    try:
        return _client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{quote(filename)}"',
            },
            ExpiresIn=settings.s3_presign_expires_seconds,
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to create a download link.") from exc
