from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_owned_business
from app.core.config import get_settings
from app.db.session import get_db
from app.models.business import Business
from app.models.document import Document, ProcessingState
from app.schemas.document import DocumentPublic, SignedUrlResponse
from app.services.document import (
    create_document,
    delete_document_record,
    get_document_for_business,
    mark_processing,
    update_stored_file,
    list_documents,
)
from app.services.indexing import (
    DocumentProcessingError,
    process_document_job,
    purge_document_resources,
    sync_business_vectors,
)
from app.services.storage import (
    MAX_FILE_BYTES,
    StorageError,
    content_type_for,
    delete_object,
    document_title,
    is_supported_filename,
    make_object_key,
    presigned_get_url,
    upload_bytes,
)

router = APIRouter(prefix="/businesses/{business_id}/documents", tags=["documents"])

UNSUPPORTED = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Unsupported file. Upload a PDF, Word (.docx), Markdown, HTML, or text file.",
)
TOO_LARGE = HTTPException(
    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    detail="File is too large. The maximum size is 20 MB.",
)


def get_owned_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    business: Business = Depends(get_owned_business),
) -> Document:
    document = get_document_for_business(db, business.id, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _require_knowledge_config() -> None:
    settings = get_settings()
    missing = []
    if not settings.s3_bucket_name.strip():
        missing.append("S3_BUCKET_NAME")
    if not settings.pinecone_api_key.strip():
        missing.append("PINECONE_API_KEY")
    if not settings.openai_api_key.strip():
        missing.append("OPENAI_API_KEY")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Knowledge base is not configured. Set "
                + ", ".join(missing)
                + " in api/.env."
            ),
        )


def _read_upload(upload: UploadFile) -> bytes:
    filename = upload.filename or ""
    if not is_supported_filename(filename):
        raise UNSUPPORTED
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise TOO_LARGE
    return data


def _store_new_file(business_id: UUID, document_id: UUID, upload: UploadFile, data: bytes) -> str:
    key = make_object_key(business_id, document_id, upload.filename or "document")
    try:
        upload_bytes(key, data, content_type_for(upload.filename or "", upload.content_type))
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return key


@router.get("", response_model=List[DocumentPublic])
def read_documents(
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
) -> List[Document]:
    return list_documents(db, business.id)


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    upload: UploadFile = File(..., alias="file"),
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
) -> Document:
    _require_knowledge_config()
    data = _read_upload(upload)
    filename = upload.filename or "document"
    document = create_document(
        db,
        business_id=business.id,
        filename=filename,
        title=document_title(filename),
        content_type=content_type_for(filename, upload.content_type),
        size_bytes=len(data),
        s3_key="",
    )
    try:
        document.s3_key = _store_new_file(business.id, document.id, upload, data)
        db.commit()
        db.refresh(document)
    except HTTPException:
        delete_document_record(db, document)
        raise

    background_tasks.add_task(process_document_job, document.id, business.id)
    return document


@router.get("/{document_id}", response_model=DocumentPublic)
def read_document(document: Document = Depends(get_owned_document)) -> Document:
    return document


@router.get("/{document_id}/download", response_model=SignedUrlResponse)
def download_document(document: Document = Depends(get_owned_document)) -> SignedUrlResponse:
    if not document.s3_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original file is not available")
    try:
        url = presigned_get_url(document.s3_key, document.filename)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return SignedUrlResponse(url=url, expires_in=get_settings().s3_presign_expires_seconds)


@router.post("/{document_id}/replace", response_model=DocumentPublic)
def replace_document(
    background_tasks: BackgroundTasks,
    upload: UploadFile = File(..., alias="file"),
    db: Session = Depends(get_db),
    document: Document = Depends(get_owned_document),
) -> Document:
    _require_knowledge_config()
    data = _read_upload(upload)
    filename = upload.filename or "document"
    new_key = _store_new_file(document.business_id, document.id, upload, data)
    try:
        purge_document_resources(document)
    except DocumentProcessingError as exc:
        try:
            delete_object(new_key)
        except StorageError:
            pass
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not remove the previous document safely. {exc.message}",
        ) from exc

    update_stored_file(
        db,
        document,
        filename=filename,
        title=document_title(filename),
        content_type=content_type_for(filename, upload.content_type),
        size_bytes=len(data),
        s3_key=new_key,
    )
    background_tasks.add_task(process_document_job, document.id, document.business_id)
    return document


@router.post("/{document_id}/reindex", response_model=DocumentPublic)
def reindex_document(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    document: Document = Depends(get_owned_document),
) -> Document:
    if not document.s3_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document has no stored file to index.",
        )
    mark_processing(db, document, ProcessingState.QUEUED)
    background_tasks.add_task(process_document_job, document.id, document.business_id)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    db: Session = Depends(get_db),
    business: Business = Depends(get_owned_business),
    document: Document = Depends(get_owned_document),
) -> None:
    remaining = [item.id for item in list_documents(db, business.id) if item.id != document.id]
    try:
        purge_document_resources(document)
        sync_business_vectors(business.id, remaining)
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
    delete_document_record(db, document)
