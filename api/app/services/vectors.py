from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence
from uuid import UUID

from pinecone import Pinecone, ServerlessSpec

from app.core.config import get_settings
from app.services.chunking import Chunk

UPSERT_BATCH = 100
DELETE_BATCH = 1000


class VectorIndexError(Exception):
    pass


def require_pinecone_config() -> None:
    settings = get_settings()
    if not settings.pinecone_api_key.strip():
        raise VectorIndexError("Pinecone is not configured. Set PINECONE_API_KEY in api/.env.")


def _client() -> Pinecone:
    require_pinecone_config()
    return Pinecone(api_key=get_settings().pinecone_api_key)


def _index_exists(client: Pinecone, name: str) -> bool:
    if hasattr(client, "has_index"):
        return bool(client.has_index(name))
    indexes = client.list_indexes()
    names = indexes.names() if hasattr(indexes, "names") else [item["name"] for item in indexes]
    return name in names


def _ensure_index() -> None:
    settings = get_settings()
    client = _client()
    if _index_exists(client, settings.pinecone_index_name):
        return
    client.create_index(
        name=settings.pinecone_index_name,
        dimension=settings.openai_embedding_dimensions,
        metric="cosine",
        spec=ServerlessSpec(
            cloud=settings.pinecone_cloud,
            region=settings.pinecone_region,
        ),
    )
    deadline = time.time() + 120
    while time.time() < deadline:
        description = client.describe_index(settings.pinecone_index_name)
        status = description.status
        ready = status.get("ready") if isinstance(status, dict) else getattr(status, "ready", False)
        if ready:
            return
        time.sleep(1)
    raise VectorIndexError("Timed out waiting for the Pinecone index to become ready.")


def _index():
    _ensure_index()
    settings = get_settings()
    return _client().Index(settings.pinecone_index_name)


def namespace_for(business_id: UUID) -> str:
    return str(business_id)


def upsert_document_chunks(
    business_id: UUID,
    document_id: UUID,
    title: str,
    language: str,
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
    updated_at: Optional[datetime] = None,
) -> int:
    if len(chunks) != len(embeddings):
        raise VectorIndexError("Embedding count does not match chunk count.")
    stamp = (updated_at or datetime.now(timezone.utc)).timestamp()
    index = _index()
    namespace = namespace_for(business_id)
    vectors = []
    for chunk, values in zip(chunks, embeddings):
        vectors.append(
            {
                "id": f"{document_id}:{chunk.order}",
                "values": list(values),
                "metadata": {
                    "business_id": str(business_id),
                    "document_id": str(document_id),
                    "document_title": title,
                    "heading_path": chunk.heading_path,
                    "language": chunk.language or language,
                    "chunk_order": chunk.order,
                    "last_update_time": stamp,
                    "text": chunk.text[:8000],
                },
            }
        )
    try:
        for start in range(0, len(vectors), UPSERT_BATCH):
            index.upsert(vectors=vectors[start : start + UPSERT_BATCH], namespace=namespace)
    except VectorIndexError:
        raise
    except Exception as exc:
        raise VectorIndexError(f"Failed to store document vectors in Pinecone. {exc}") from exc
    return len(vectors)


def _is_missing_target(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "namespace not found",
            "index not found",
            "404",
        )
    )


def _delete_ids(index, namespace: str, ids: Sequence[str]) -> None:
    unique = list(dict.fromkeys(ids))
    for start in range(0, len(unique), DELETE_BATCH):
        batch = unique[start : start + DELETE_BATCH]
        if batch:
            index.delete(ids=batch, namespace=namespace)


def _list_ids(index, namespace: str, prefix: Optional[str] = None) -> List[str]:
    found: List[str] = []
    kwargs = {"namespace": namespace}
    if prefix:
        kwargs["prefix"] = prefix
    for page in index.list(**kwargs):
        found.extend(page)
    return found


def delete_document_vectors(
    business_id: UUID,
    document_id: UUID,
    chunk_count: int = 0,
) -> None:
    settings = get_settings()
    if not settings.pinecone_api_key.strip():
        return
    client = _client()
    if not _index_exists(client, settings.pinecone_index_name):
        return
    index = client.Index(settings.pinecone_index_name)
    namespace = namespace_for(business_id)
    prefix = f"{document_id}:"
    ids: List[str] = [f"{document_id}:{order}" for order in range(max(chunk_count, 0))]
    try:
        ids.extend(_list_ids(index, namespace, prefix=prefix))
    except Exception as exc:
        if not _is_missing_target(exc):
            raise VectorIndexError("Failed to list document vectors in Pinecone.") from exc
        return
    try:
        _delete_ids(index, namespace, ids)
    except Exception as exc:
        if _is_missing_target(exc):
            return
        raise VectorIndexError("Failed to delete document vectors from Pinecone.") from exc
    try:
        index.delete(
            namespace=namespace,
            filter={"document_id": {"$eq": str(document_id)}},
        )
    except Exception:
        pass


def purge_orphan_vectors(business_id: UUID, keep_document_ids: Iterable[UUID]) -> None:
    settings = get_settings()
    if not settings.pinecone_api_key.strip():
        return
    client = _client()
    if not _index_exists(client, settings.pinecone_index_name):
        return
    keep = {str(item) for item in keep_document_ids}
    if not keep:
        delete_business_vectors(business_id)
        return
    index = client.Index(settings.pinecone_index_name)
    namespace = namespace_for(business_id)
    try:
        ids = _list_ids(index, namespace)
    except Exception as exc:
        if _is_missing_target(exc):
            return
        raise VectorIndexError("Failed to list business vectors in Pinecone.") from exc
    stale = [vector_id for vector_id in ids if vector_id.split(":", 1)[0] not in keep]
    try:
        _delete_ids(index, namespace, stale)
    except Exception as exc:
        if _is_missing_target(exc):
            return
        raise VectorIndexError("Failed to delete leftover document vectors from Pinecone.") from exc


def delete_business_vectors(business_id: UUID) -> None:
    settings = get_settings()
    if not settings.pinecone_api_key.strip():
        return
    client = _client()
    if not _index_exists(client, settings.pinecone_index_name):
        return
    try:
        client.Index(settings.pinecone_index_name).delete(
            delete_all=True,
            namespace=namespace_for(business_id),
        )
    except Exception as exc:
        if _is_missing_target(exc):
            return
        raise VectorIndexError("Failed to delete business vectors from Pinecone.") from exc


def query_business(
    business_id: UUID,
    vector: List[float],
    top_k: int = 8,
    document_ids: Optional[Sequence[UUID]] = None,
) -> Iterable[dict]:
    """Search one workspace only. Namespace and metadata filter are both required."""
    live_ids = [str(item) for item in document_ids] if document_ids is not None else None
    if live_ids is not None and not live_ids:
        return []
    metadata_filter: dict = {"business_id": {"$eq": str(business_id)}}
    if live_ids:
        metadata_filter["document_id"] = {"$in": live_ids}
    try:
        result = _index().query(
            namespace=namespace_for(business_id),
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter,
        )
    except Exception as exc:
        if _is_missing_target(exc):
            return []
        raise VectorIndexError("Failed to search this business's documents.") from exc
    matches = result.get("matches", []) if isinstance(result, dict) else result.matches
    return matches or []
