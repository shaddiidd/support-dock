from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    filename: str
    title: str
    content_type: str
    size_bytes: int
    status: str
    processing_state: str
    error_code: Optional[str]
    error_message: Optional[str]
    indexed_chunk_count: int
    language: Optional[str]
    languages: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int
