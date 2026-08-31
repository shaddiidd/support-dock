from __future__ import annotations

from typing import List, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)

CATEGORIES = {
    TicketCategory.PAYMENT,
    TicketCategory.BUG,
    TicketCategory.ACCOUNT,
    TicketCategory.REFUND,
    TicketCategory.COMPLAINT,
    TicketCategory.SECURITY,
    TicketCategory.HUMAN_REQUEST,
    TicketCategory.UNRESOLVED,
}
PRIORITIES = {
    TicketPriority.LOW,
    TicketPriority.MEDIUM,
    TicketPriority.HIGH,
    TicketPriority.URGENT,
}


def list_tickets(db: Session, business_id: UUID) -> List[Ticket]:
    statement = (
        select(Ticket)
        .where(Ticket.business_id == business_id)
        .order_by(Ticket.created_at.desc())
    )
    return list(db.scalars(statement))


def get_ticket(db: Session, business_id: UUID, ticket_id: UUID) -> Optional[Ticket]:
    statement = select(Ticket).where(
        Ticket.id == ticket_id,
        Ticket.business_id == business_id,
    )
    return db.scalar(statement)


def get_ticket_for_conversation(
    db: Session,
    business_id: UUID,
    conversation_id: UUID,
) -> Optional[Ticket]:
    statement = select(Ticket).where(
        Ticket.business_id == business_id,
        Ticket.conversation_id == conversation_id,
    )
    return db.scalar(statement)


def create_ticket(
    db: Session,
    *,
    business_id: UUID,
    conversation_id: UUID,
    title: str,
    summary: str,
    category: str,
    priority: str,
    internal_reason: str,
    customer_language: str,
    customer_email: str,
    customer_phone: Optional[str],
    messages: Sequence[dict],
) -> Ticket:
    ticket = Ticket(
        business_id=business_id,
        conversation_id=conversation_id,
        number=_ticket_number(),
        title=_clip(title, 180) or "Support request",
        summary=_clip(summary, 2000) or "A customer needs human support.",
        category=category if category in CATEGORIES else TicketCategory.UNRESOLVED,
        priority=priority if priority in PRIORITIES else TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        internal_reason=_clip(internal_reason, 2000) or "The assistant decided a human is needed.",
        customer_language=customer_language or "en",
        customer_email=_clip(customer_email, 255).lower() or None,
        customer_phone=_clip(customer_phone or "", 40) or None,
        messages=list(messages),
        email_status="pending",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def mark_email_status(db: Session, ticket: Ticket, status: str, error: Optional[str] = None) -> Ticket:
    ticket.email_status = status
    ticket.email_error = error
    db.commit()
    db.refresh(ticket)
    return ticket


def _ticket_number() -> str:
    return "T-" + uuid4().hex[:8].upper()


def _clip(value: str, limit: int) -> str:
    text = " ".join((value or "").split())
    return text[:limit].strip()
