from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business import Business


class TicketStatus:
    OPEN = "open"
    CLOSED = "closed"


class TicketCategory:
    PAYMENT = "payment"
    BUG = "bug"
    ACCOUNT = "account"
    REFUND = "refund"
    COMPLAINT = "complaint"
    SECURITY = "security"
    HUMAN_REQUEST = "human_request"
    UNRESOLVED = "unresolved"


class TicketPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("business_id", "conversation_id", name="uq_tickets_business_conversation"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    conversation_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=TicketStatus.OPEN, nullable=False)
    internal_reason: Mapped[str] = mapped_column(Text, nullable=False)
    customer_language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    messages: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)
    email_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    email_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    business: Mapped["Business"] = relationship(back_populates="tickets")
