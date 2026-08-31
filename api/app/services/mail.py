from __future__ import annotations

import html
import logging
from typing import Optional

import resend

from app.core.config import get_settings
from app.models.business import Business
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)


class MailError(Exception):
    pass


def notify_support_ticket(business: Business, ticket: Ticket) -> str:
    settings = get_settings()
    if not settings.resend_api_key.strip() or not settings.resend_from_email.strip():
        return "skipped"
    if not (business.support_email or "").strip():
        return "skipped"

    transcript = _transcript_html(ticket)
    customer = _customer_html(ticket)
    body = f"""
    <p>A support ticket was opened for <strong>{html.escape(business.name)}</strong>.</p>
    <p>
      <strong>Ticket:</strong> {html.escape(ticket.number)}<br>
      <strong>Priority:</strong> {html.escape(ticket.priority)}<br>
      <strong>Category:</strong> {html.escape(ticket.category)}
    </p>
    {customer}
    <h3>{html.escape(ticket.title)}</h3>
    <p>{html.escape(ticket.summary)}</p>
    <p><strong>Why it was escalated</strong></p>
    <p>{html.escape(ticket.internal_reason)}</p>
    <p><strong>Conversation</strong></p>
    {transcript}
    """
    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [business.support_email.strip()],
                "subject": f"[{ticket.priority.upper()}] {ticket.number}: {ticket.title}",
                "html": body,
            }
        )
    except Exception as exc:
        logger.exception("Failed to send ticket email for %s", ticket.number)
        raise MailError(str(exc)) from exc
    return "sent"


def _customer_html(ticket: Ticket) -> str:
    parts = []
    email = (ticket.customer_email or "").strip()
    phone = (ticket.customer_phone or "").strip()
    if email:
        safe = html.escape(email)
        parts.append(f'<a href="mailto:{safe}">{safe}</a>')
    if phone:
        safe = html.escape(phone)
        href = html.escape(_tel_href(phone))
        parts.append(f'<a href="tel:{href}">{safe}</a>')
    if not parts:
        return ""
    return "<p><strong>Customer:</strong> " + " · ".join(parts) + "</p>"


def _tel_href(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if phone.strip().startswith("+"):
        return f"+{digits}"
    return digits


def _transcript_html(ticket: Ticket) -> str:
    rows = []
    for item in ticket.messages or []:
        role = html.escape(str(item.get("role") or "user").title())
        content = html.escape(str(item.get("content") or "")).replace("\n", "<br>")
        rows.append(f"<p><strong>{role}:</strong><br>{content}</p>")
    return "".join(rows) or "<p>No conversation history.</p>"
