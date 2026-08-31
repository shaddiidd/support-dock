from __future__ import annotations

import logging
from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document import Document, ProcessingState
from app.services.chunking import chunk_document
from app.services.language import majority_language, unique_languages
from app.services.document import (
    get_document_for_business,
    mark_failed,
    mark_processing,
    mark_ready,
)
from app.services.embeddings import EmbeddingError, embed_texts
from app.services.extraction import ExtractionError, extract_text
from app.services.storage import StorageError, delete_object, delete_prefix, download_bytes
from app.services.vectors import (
    VectorIndexError,
    delete_business_vectors,
    delete_document_vectors,
    purge_orphan_vectors,
    upsert_document_chunks,
)

logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def process_document_job(document_id: UUID, business_id: UUID) -> None:
    db = SessionLocal()
    try:
        process_document(db, document_id, business_id)
    finally:
        db.close()


def process_document(db: Session, document_id: UUID, business_id: UUID) -> None:
    document = get_document_for_business(db, business_id, document_id)
    if document is None:
        return
    try:
        mark_processing(db, document, ProcessingState.EXTRACTING)
        payload = download_bytes(document.s3_key)
        text = extract_text(document.filename, document.content_type, payload)

        mark_processing(db, document, ProcessingState.CHUNKING)
        chunks = chunk_document(document.title, text)
        if not chunks:
            raise DocumentProcessingError(
                "extraction_failed",
                "No indexable content was found after cleaning this document.",
            )
        chunk_langs = [chunk.language for chunk in chunks]
        chunk_languages = unique_languages(chunk_langs)
        language = majority_language(chunk_langs)
        logger.info(
            "Detected chunk languages for document %s: %s (majority=%s)",
            document.id,
            chunk_languages,
            language,
        )

        mark_processing(db, document, ProcessingState.EMBEDDING)
        embeddings = embed_texts([chunk.text for chunk in chunks])

        mark_processing(db, document, ProcessingState.INDEXING)
        delete_document_vectors(
            document.business_id,
            document.id,
            chunk_count=document.indexed_chunk_count,
        )
        count = upsert_document_chunks(
            business_id=document.business_id,
            document_id=document.id,
            title=document.title,
            language=language,
            chunks=chunks,
            embeddings=embeddings,
            updated_at=document.updated_at,
        )
        mark_ready(
            db,
            document,
            chunk_count=count,
            language=language,
            languages=chunk_languages,
        )
    except DocumentProcessingError as exc:
        mark_failed(db, document, exc.code, exc.message)
    except StorageError as exc:
        mark_failed(db, document, "upload_failed", str(exc))
    except ExtractionError as exc:
        mark_failed(db, document, "extraction_failed", str(exc))
    except EmbeddingError as exc:
        mark_failed(db, document, "embedding_failed", str(exc))
    except VectorIndexError as exc:
        mark_failed(db, document, "indexing_failed", str(exc))
    except Exception:
        logger.exception("Unexpected document processing failure for %s", document_id)
        mark_failed(
            db,
            document,
            "indexing_failed",
            "Indexing failed unexpectedly. Try uploading the document again.",
        )


def purge_document_resources(document: Document) -> None:
    try:
        delete_document_vectors(
            document.business_id,
            document.id,
            chunk_count=document.indexed_chunk_count,
        )
    except VectorIndexError as exc:
        raise DocumentProcessingError("indexing_failed", str(exc)) from exc
    if document.s3_key:
        try:
            delete_object(document.s3_key)
        except StorageError as exc:
            raise DocumentProcessingError("upload_failed", str(exc)) from exc


def sync_business_vectors(business_id: UUID, keep_document_ids: Sequence[UUID]) -> None:
    try:
        purge_orphan_vectors(business_id, keep_document_ids)
    except VectorIndexError as exc:
        raise DocumentProcessingError("indexing_failed", str(exc)) from exc


def purge_business_knowledge(business_id: UUID) -> None:
    try:
        delete_prefix(f"businesses/{business_id}/")
    except StorageError:
        logger.exception("Failed to delete S3 objects for business %s", business_id)
    try:
        delete_business_vectors(business_id)
    except VectorIndexError:
        logger.exception("Failed to delete Pinecone vectors for business %s", business_id)
