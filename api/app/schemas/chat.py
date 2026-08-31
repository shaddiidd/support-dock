from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ticket import TicketBrief


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: List[ChatTurn] = Field(default_factory=list, max_length=16)
    conversation_id: Optional[UUID] = None


class ChatSource(BaseModel):
    document_id: Optional[UUID] = None
    document_title: str
    heading_path: str = ""


class ChatResponse(BaseModel):
    reply: str
    refused: bool = False
    sources: List[ChatSource] = Field(default_factory=list)
    conversation_id: UUID
    chat_closed: bool = False
    ticket: Optional[TicketBrief] = None
