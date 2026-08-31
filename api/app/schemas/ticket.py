from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TicketMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class TicketPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    number: str
    title: str
    summary: str
    category: str
    priority: str
    status: str
    internal_reason: str
    customer_language: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    messages: List[TicketMessage] = Field(default_factory=list)
    email_status: str
    email_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TicketBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    title: str
    status: str
    category: str
    priority: str
