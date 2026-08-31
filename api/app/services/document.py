from typing import List, Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.document import Document, DocumentStatus, ProcessingState
from app.services.language import unique_languages


def list_documents(db: Session, business_id: UUID) -> List[Document]:
    statement = (
        select(Document)
        .where(Document.business_id == business_id)
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(statement))


def get_document_for_business(
    db: Session,
    business_id: UUID,
    document_id: UUID,
) -> Optional[Document]:
    statement = select(Document).where(
        Document.id == document_id,
        Document.business_id == business_id,
    )
    return db.scalar(statement)


def create_document(
    db: Session,
    *,
    business_id: UUID,
    filename: str,
    title: str,
    content_type: str,
    size_bytes: int,
    s3_key: str,
) -> Document:
    document = Document(
        business_id=business_id,
        filename=filename,
        title=title,
        content_type=content_type,
        size_bytes=size_bytes,
        s3_key=s3_key,
        status=DocumentStatus.UPLOADED,
        processing_state=ProcessingState.QUEUED,
        indexed_chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def mark_processing(db: Session, document: Document, state: str) -> Document:
    document.status = DocumentStatus.PROCESSING
    document.processing_state = state
    document.error_code = None
    document.error_message = None
    db.commit()
    db.refresh(document)
    return document


def mark_ready(
    db: Session,
    document: Document,
    *,
    chunk_count: int,
    language: str,
    languages: Optional[Sequence[str]] = None,
) -> Document:
    document.status = DocumentStatus.READY
    document.processing_state = ProcessingState.COMPLETE
    document.indexed_chunk_count = chunk_count
    document.language = language
    document.languages = unique_languages(languages or ([language] if language else []))
    document.error_code = None
    document.error_message = None
    db.commit()
    db.refresh(document)
    refresh_business_languages(db, document.business_id)
    db.refresh(document)
    return document


def mark_failed(db: Session, document: Document, code: str, message: str) -> Document:
    document.status = DocumentStatus.FAILED
    document.processing_state = ProcessingState.FAILED
    document.indexed_chunk_count = 0
    document.language = None
    document.languages = []
    document.error_code = code
    document.error_message = message
    db.commit()
    db.refresh(document)
    refresh_business_languages(db, document.business_id)
    db.refresh(document)
    return document


def update_stored_file(
    db: Session,
    document: Document,
    *,
    filename: str,
    title: str,
    content_type: str,
    size_bytes: int,
    s3_key: str,
) -> Document:
    document.filename = filename
    document.title = title
    document.content_type = content_type
    document.size_bytes = size_bytes
    document.s3_key = s3_key
    document.status = DocumentStatus.UPLOADED
    document.processing_state = ProcessingState.QUEUED
    document.indexed_chunk_count = 0
    document.language = None
    document.languages = []
    document.error_code = None
    document.error_message = None
    db.commit()
    db.refresh(document)
    refresh_business_languages(db, document.business_id)
    return document


def delete_document_record(db: Session, document: Document) -> None:
    business_id = document.business_id
    db.delete(document)
    db.commit()
    refresh_business_languages(db, business_id)


def refresh_business_languages(db: Session, business_id: UUID) -> List[str]:
    business = db.get(Business, business_id)
    if business is None:
        return []
    found = []
    for document in list_documents(db, business_id):
        if document.status != DocumentStatus.READY:
            continue
        found.extend(document.languages or [])
        if document.language:
            found.append(document.language)
    business.knowledge_languages = unique_languages(found)
    db.commit()
    db.refresh(business)
    return list(business.knowledge_languages or [])
