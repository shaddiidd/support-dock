from __future__ import annotations

from typing import List, Sequence

from openai import OpenAI

from app.core.config import get_settings

BATCH_SIZE = 64


class EmbeddingError(Exception):
    pass


def require_embedding_config() -> None:
    settings = get_settings()
    if not settings.openai_api_key.strip():
        raise EmbeddingError("OpenAI is not configured. Set OPENAI_API_KEY in api/.env.")


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    require_embedding_config()
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    vectors: List[List[float]] = []
    try:
        for start in range(0, len(texts), BATCH_SIZE):
            batch = list(texts[start : start + BATCH_SIZE])
            response = client.embeddings.create(
                model=settings.openai_embedding_model,
                input=batch,
                dimensions=settings.openai_embedding_dimensions,
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend(item.embedding for item in ordered)
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError(
            f"Failed to create embeddings for this document. {exc}"
        ) from exc
    return vectors
