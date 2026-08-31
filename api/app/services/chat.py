from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Sequence
from uuid import UUID, uuid4

from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.models.business import Business
from app.models.document import DocumentStatus
from app.schemas.chat import ChatResponse, ChatSource, ChatTurn
from app.schemas.ticket import TicketBrief
from app.services.document import list_documents, refresh_business_languages
from app.services.embeddings import EmbeddingError, embed_texts
from app.services.language import detect_language, language_name, translate_query, unique_languages
from app.services.mail import MailError, notify_support_ticket
from app.services.ticket import (
    create_ticket,
    get_ticket_for_conversation,
    mark_email_status,
)
from app.services.vectors import VectorIndexError, query_business

logger = logging.getLogger("support_dock.retrieval")

REFUSAL_TEMPLATE = (
    "I can only help with questions about {name}. "
    "I'm not able to answer that."
)

SMALL_TALK = re.compile(
    r"^\s*(hi|hello|hey|yo|sup|good\s+(morning|afternoon|evening)|"
    r"thanks?( you)?|thank you|cheers|bye|goodbye|good night|see you|"
    r"how are you\??|what's up\??|whats up\??)\s*[!.?]*\s*$",
    re.I,
)

CONTACT_ASK = re.compile(
    r"\b(phone|email|e-mail|call|contact|reach|number|hotline|"
    r"whatsapp|telegram|mobile|cell|website|web\s*site|url|homepage|site|"
    r"address|about|who are you|company|business)\b|"
    r"ايميل|بريد|هاتف|جوال|موبايل|رقم|تواصل|موقع|ويب",
    re.I,
)


class ChatError(Exception):
    pass


def refuse_message(business_name: str) -> str:
    return REFUSAL_TEMPLATE.format(name=business_name.strip() or "this business")


def answer_question(
    db: Session,
    business: Business,
    message: str,
    history: Sequence[ChatTurn],
    conversation_id: Optional[UUID] = None,
) -> ChatResponse:
    settings = get_settings()
    if not settings.openai_api_key.strip():
        raise ChatError("OpenAI is not configured. Set OPENAI_API_KEY in api/.env.")

    text = message.strip()
    conversation_id = conversation_id or uuid4()
    customer_language = detect_language(text)

    existing = get_ticket_for_conversation(db, business.id, conversation_id)
    if existing:
        return ChatResponse(
            reply=_closed_reply(existing.number, customer_language),
            conversation_id=conversation_id,
            chat_closed=True,
            ticket=TicketBrief.model_validate(existing),
        )

    if SMALL_TALK.match(text):
        return ChatResponse(
            reply=_small_talk_reply(business.name, text),
            refused=False,
            conversation_id=conversation_id,
        )

    customer_email, customer_phone = _customer_contact(history, text, business)

    matches = _retrieve(db, business, text, history, customer_language)
    excerpts = _format_excerpts(matches)
    try:
        payload = _complete(
            business,
            text,
            history,
            excerpts,
            bool(matches),
            customer_language,
            customer_email,
            customer_phone,
        )
    except Exception as exc:
        raise ChatError("The assistant could not answer right now. Try again.") from exc

    kind = str(payload.get("type") or "").strip().lower()
    reply = str(payload.get("reply") or "").strip()
    if kind != "escalate" and _ready_to_open_ticket(history, text, customer_email):
        kind = "escalate"
        payload.setdefault("ticket", {})
    if kind == "small_talk" and reply:
        return ChatResponse(reply=reply, refused=False, conversation_id=conversation_id)
    if kind == "follow_up" and reply:
        return ChatResponse(reply=reply, refused=False, conversation_id=conversation_id)
    if kind == "answer" and reply and (
        matches or (CONTACT_ASK.search(text) and _business_profile_lines(business))
    ):
        return ChatResponse(
            reply=reply,
            refused=False,
            sources=_sources(matches),
            conversation_id=conversation_id,
        )
    if kind == "escalate":
        if not customer_email:
            return ChatResponse(
                reply=_ask_contact_reply(customer_language),
                refused=False,
                conversation_id=conversation_id,
            )
        return _open_ticket(
            db,
            business,
            text,
            history,
            payload,
            reply,
            conversation_id,
            customer_language,
            customer_email,
            customer_phone,
        )
    return ChatResponse(
        reply=reply or refuse_message(business.name),
        refused=True,
        conversation_id=conversation_id,
    )


def _small_talk_reply(business_name: str, text: str) -> str:
    lowered = text.lower()
    name = business_name.strip() or "us"
    if re.search(r"bye|goodbye|good night|see you", lowered):
        return f"Goodbye. Come back anytime you have a {name} question."
    if re.search(r"thanks|thank you|cheers", lowered):
        return f"You're welcome. Ask whenever you need help with {name}."
    if re.search(r"how are you|what's up|whats up", lowered):
        return "I'm doing well. How can I help you today?"
    return f"Hello. How can I help you with {name} today?"


def _closed_reply(ticket_number: str, language: str) -> str:
    if language == "ar":
        return f"هذه المحادثة مغلقة. التذكرة {ticket_number} مفتوحة بالفعل."
    return f"This conversation is closed. Ticket {ticket_number} is already open."


def _open_ticket(
    db: Session,
    business: Business,
    message: str,
    history: Sequence[ChatTurn],
    payload: dict,
    reply: str,
    conversation_id: UUID,
    customer_language: str,
    customer_email: str,
    customer_phone: Optional[str],
) -> ChatResponse:
    existing = get_ticket_for_conversation(db, business.id, conversation_id)
    if existing:
        return ChatResponse(
            reply=_closed_reply(existing.number, customer_language),
            conversation_id=conversation_id,
            chat_closed=True,
            ticket=TicketBrief.model_validate(existing),
        )

    details = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else {}
    transcript = [
        {"role": item.role, "content": item.content}
        for item in history
        if item.role in {"user", "assistant"}
    ]
    transcript.append({"role": "user", "content": message})
    customer_reply = reply or "A teammate will take it from here."
    issue = _issue_from_history(history, message)
    ticket = create_ticket(
        db,
        business_id=business.id,
        conversation_id=conversation_id,
        title=str(details.get("title") or issue or "Support request"),
        summary=str(details.get("summary") or issue or message),
        category=str(details.get("category") or "unresolved"),
        priority=str(details.get("priority") or "medium"),
        internal_reason=str(details.get("internal_reason") or "The assistant decided a human is needed."),
        customer_language=customer_language,
        customer_email=customer_email,
        customer_phone=customer_phone,
        messages=[*transcript, {"role": "assistant", "content": customer_reply}],
    )
    try:
        status = notify_support_ticket(business, ticket)
        mark_email_status(db, ticket, status)
    except MailError as exc:
        mark_email_status(db, ticket, "failed", str(exc))

    if ticket.number not in customer_reply:
        customer_reply = (
            f"{customer_reply.rstrip()}\n\nTicket {ticket.number}. This conversation is now closed."
        )
        ticket.messages = [*transcript, {"role": "assistant", "content": customer_reply}]
        flag_modified(ticket, "messages")
        db.commit()
        db.refresh(ticket)

    return ChatResponse(
        reply=customer_reply,
        conversation_id=conversation_id,
        chat_closed=True,
        ticket=TicketBrief.model_validate(ticket),
    )


def _retrieve(
    db: Session,
    business: Business,
    message: str,
    history: Sequence[ChatTurn],
    customer_language: str,
) -> List[dict]:
    search = message
    previous = [item.content for item in history if item.role == "user"]
    if previous:
        search = f"{previous[-1]}\n{message}"

    kb_languages = _knowledge_languages(db, business)
    live_ids = _live_document_ids(db, business.id)
    if not live_ids:
        _log_retrieval(
            business_id=str(business.id),
            original_question=message,
            search_text=search,
            detected_language=customer_language,
            knowledge_languages=kb_languages,
            original_top_score=None,
            original_hit_count=0,
            weak_original=True,
            translated_queries=[],
            retrieval_path="none",
            winning_path="none",
            chunks=[],
        )
        return []
    original_hits = _search_business(
        business.id, search, path="original", document_ids=live_ids
    )
    useful_original = _filter_useful(business.id, original_hits, live_ids)

    translated_queries = []
    useful_translated: List[dict] = []
    retrieval_path = "original"
    language_mismatch = bool(kb_languages) and customer_language not in kb_languages

    if _is_weak(useful_original) or language_mismatch:
        targets = [lang for lang in kb_languages if lang != customer_language]
        for target in targets:
            translated = translate_query(search, target)
            if not translated or translated.strip() == search.strip():
                translated_queries.append(
                    {
                        "language": target,
                        "query": translated,
                        "skipped": True,
                    }
                )
                continue
            translated_queries.append({"language": target, "query": translated})
            hits = _search_business(
                business.id,
                translated,
                path=f"translated:{target}",
                document_ids=live_ids,
            )
            useful_translated.extend(_filter_useful(business.id, hits, live_ids))
        if translated_queries:
            retrieval_path = "original+translated" if useful_original else "translated"

    merged = _merge_rank([*useful_original, *useful_translated])[:6]
    winning_path = merged[0]["retrieval_path"] if merged else "none"
    _log_retrieval(
        business_id=str(business.id),
        original_question=message,
        search_text=search,
        detected_language=customer_language,
        knowledge_languages=kb_languages,
        original_top_score=_top_score(useful_original),
        original_hit_count=len(useful_original),
        weak_original=_is_weak(useful_original),
        language_mismatch=language_mismatch,
        translated_queries=translated_queries,
        retrieval_path=retrieval_path,
        winning_path=winning_path,
        chunks=[_log_chunk(item) for item in merged],
    )
    return merged


def _knowledge_languages(db: Session, business: Business) -> List[str]:
    stored = unique_languages(business.knowledge_languages or [])
    if stored:
        return stored
    return refresh_business_languages(db, business.id)


def _live_document_ids(db: Session, business_id: UUID) -> List[UUID]:
    return [
        item.id
        for item in list_documents(db, business_id)
        if item.status == DocumentStatus.READY
    ]


def _search_business(
    business_id: UUID,
    query: str,
    path: str,
    document_ids: Optional[Sequence[UUID]] = None,
) -> List[dict]:
    try:
        vector = embed_texts([query])[0]
        raw = query_business(business_id, vector, top_k=8, document_ids=document_ids)
    except (EmbeddingError, VectorIndexError):
        logger.exception("Search failed for path=%s business=%s", path, business_id)
        return []
    items = []
    for match in raw:
        item = _as_match(match)
        item["retrieval_path"] = path
        items.append(item)
    return items


def _filter_useful(
    business_id: UUID,
    matches: Sequence[dict],
    document_ids: Optional[Sequence[UUID]] = None,
) -> List[dict]:
    settings = get_settings()
    allowed = {str(item) for item in document_ids} if document_ids is not None else None
    useful = []
    for item in matches:
        if item["score"] < settings.chat_min_score:
            continue
        metadata = item["metadata"]
        if str(metadata.get("business_id") or "") != str(business_id):
            continue
        if allowed is not None and str(metadata.get("document_id") or "") not in allowed:
            continue
        if not (metadata.get("text") or "").strip():
            continue
        useful.append(item)
    return useful


def _is_weak(matches: Sequence[dict]) -> bool:
    if not matches:
        return True
    return _top_score(matches) < get_settings().chat_strong_score


def _top_score(matches: Sequence[dict]) -> Optional[float]:
    if not matches:
        return None
    return max(float(item["score"]) for item in matches)


def _merge_rank(matches: Sequence[dict]) -> List[dict]:
    best = {}
    for item in matches:
        key = item.get("id") or ""
        if not key:
            continue
        existing = best.get(key)
        if existing is None or item["score"] > existing["score"]:
            best[key] = item
    return sorted(best.values(), key=lambda item: item["score"], reverse=True)


def _as_match(match) -> dict:
    if isinstance(match, dict):
        metadata = match.get("metadata") or {}
        return {
            "id": match.get("id") or "",
            "score": float(match.get("score") or 0),
            "metadata": metadata,
        }
    metadata = getattr(match, "metadata", None) or {}
    return {
        "id": getattr(match, "id", "") or "",
        "score": float(getattr(match, "score", 0) or 0),
        "metadata": metadata,
    }


def _format_excerpts(matches: Sequence[dict]) -> str:
    if not matches:
        return ""
    blocks = []
    for index, match in enumerate(matches, start=1):
        meta = match["metadata"]
        title = meta.get("document_title") or "Document"
        heading = meta.get("heading_path") or ""
        label = f"{title} > {heading}" if heading else title
        blocks.append(f"[{index}] {label}\n{meta.get('text', '').strip()}")
    return "\n\n".join(blocks)


def _sources(matches: Sequence[dict]) -> List[ChatSource]:
    seen = set()
    sources: List[ChatSource] = []
    for match in matches:
        meta = match["metadata"]
        title = str(meta.get("document_title") or "Document")
        heading = str(meta.get("heading_path") or "")
        key = (title, heading)
        if key in seen:
            continue
        seen.add(key)
        document_id = meta.get("document_id")
        try:
            parsed_id = UUID(str(document_id)) if document_id else None
        except ValueError:
            parsed_id = None
        sources.append(
            ChatSource(
                document_id=parsed_id,
                document_title=title,
                heading_path=heading,
            )
        )
    return sources[:4]


def _complete(
    business: Business,
    message: str,
    history: Sequence[ChatTurn],
    excerpts: str,
    has_context: bool,
    customer_language: str,
    customer_email: Optional[str],
    customer_phone: Optional[str],
) -> dict:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    refusal = refuse_message(business.name)
    reply_language = language_name(customer_language)
    extra = (business.assistant_instructions or "").strip()
    extra_block = (
        "\nExtra instructions from the business owner "
        "(tone, things to watch for, or how to handle this workspace). "
        "They cannot invent facts or override the rules below:\n"
        f"{extra}\n"
        if extra
        else ""
    )
    profile_block = _format_business_profile(business)
    profile_rule = (
        "- Answer questions about this business using the business profile below "
        "(name, description, website, public email, and phone).\n"
        if profile_block
        else ""
    )
    if customer_email:
        ticket_contact_rule = (
            f"The customer has already given their email ({customer_email})"
            + (f" and phone ({customer_phone})" if customer_phone else "")
            + ". You may use type \"escalate\" when a human is needed.\n"
        )
    else:
        ticket_contact_rule = (
            "The customer has not given their email yet. "
            "You cannot open a ticket. If a human is needed, use type \"follow_up\" "
            "and ask for their email. A phone number is optional.\n"
        )
    system = f"""You are the support assistant for {business.name}.

The customer's language was detected as {reply_language}.
Write the entire reply in {reply_language}. No other language.
{extra_block}
You may:
- Reply to greetings, thanks, and goodbyes briefly.
- Answer questions using ONLY the document excerpts and the business profile provided.
{profile_rule}- Ask one short follow-up if the issue is unclear.
- Try the relevant steps from the excerpts before escalating.

Escalate to a human only when a person must take action, such as:
- payment or purchase failure
- bug or error
- account-access issue
- refund or complaint
- security concern
- an explicit request for a human
- the problem is still unresolved after you already tried the available guidance

A ticket requires the customer's email address from one of their messages. Phone is optional.
{ticket_contact_rule}If they just sent their email after you asked for it, and a human is still needed, use type "escalate".

Do not escalate normal questions that the documents can answer.
Do not escalate just because the excerpts are incomplete, unless the customer needs a human to do something.

You must not:
- Use general world knowledge, other companies, news, math, coding, or personal opinions.
- Invent policies, prices, hours, procedures, phone numbers, email addresses, or website URLs.
- Invent a customer email or phone number.
- Share any ticket or support inbox. Only the public contact details in the business profile.
- Use earlier conversation turns as a source of facts. Only the current excerpts and business profile count.
- Mention translation, language detection, source documents, a knowledge base, or this workspace.
- Tell the customer that you are reading files or excerpts.

Return a JSON object with:
- "type": "small_talk" | "answer" | "follow_up" | "escalate" | "refuse"
- "reply": the customer-facing message, written in {reply_language}
- "ticket": only when type is "escalate". Object with:
  - "title": short title
  - "summary": concise issue summary
  - "category": payment | bug | account | refund | complaint | security | human_request | unresolved
  - "priority": low | medium | high | urgent
  - "internal_reason": why a human is needed (not shown to the customer)

When type is "escalate", keep "reply" concise and helpful. Do not mention internal_reason.
When type is "refuse", write this meaning in {reply_language}:
{refusal}
"""
    parts = []
    if profile_block:
        parts.append(profile_block)
    if has_context:
        parts.append(f"Document excerpts:\n{excerpts}")
    else:
        parts.append(
            "Document excerpts: none."
            + (
                " You may still share the business profile above if asked."
                if profile_block
                else " Unless the user is only greeting, thanking, or saying goodbye, you must refuse."
            )
        )
    context_block = "\n\n".join(parts)

    messages = [{"role": "system", "content": system}]
    for turn in history[-12:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(
        {
            "role": "user",
            "content": f"{context_block}\n\nUser message:\n{message}",
        }
    )

    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.1,
        max_tokens=700,
        response_format={"type": "json_object"},
        messages=messages,
    )
    content = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"type": "refuse", "reply": refusal}
    if not isinstance(parsed, dict):
        return {"type": "refuse", "reply": refusal}
    return parsed


EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+|00)?(?:\d[\s().\-]*){7,14}\d(?!\w)")


def _customer_contact(
    history: Sequence[ChatTurn],
    message: str,
    business: Business,
) -> tuple[Optional[str], Optional[str]]:
    blocked_emails = {
        (business.contact_email or "").strip().lower(),
        (business.support_email or "").strip().lower(),
    }
    blocked_emails.discard("")
    blocked_phone = re.sub(r"\D", "", business.contact_phone or "")

    blobs = [item.content for item in history if item.role == "user"]
    blobs.append(message)
    combined = "\n".join(blobs)

    emails = [
        match.group(0).lower()
        for match in EMAIL_RE.finditer(combined)
        if match.group(0).lower() not in blocked_emails
    ]
    email = emails[-1] if emails else None

    phone = None
    for match in PHONE_RE.finditer(combined):
        raw = " ".join(match.group(0).split())
        digits = re.sub(r"\D", "", raw)
        if blocked_phone and digits.endswith(blocked_phone):
            continue
        if 8 <= len(digits) <= 15:
            phone = raw
    return email, phone


def _ask_contact_reply(language: str) -> str:
    if language == "ar":
        return (
            "قبل فتح تذكرة أحتاج بريدك الإلكتروني. "
            "يمكنك أيضاً إرسال رقم هاتفك، لكنه اختياري."
        )
    return (
        "Before I open a ticket, I need your email address. "
        "A phone number is optional if you want us to call you."
    )


def _ready_to_open_ticket(
    history: Sequence[ChatTurn],
    message: str,
    customer_email: Optional[str],
) -> bool:
    if not customer_email or not EMAIL_RE.search(message):
        return False
    previous = ""
    for item in reversed(list(history)):
        if item.role == "assistant":
            previous = item.content
            break
    return bool(
        re.search(
            r"your email|need your email|email address|before i open a ticket|"
            r"بريدك|بريد إلكتروني|قبل فتح تذكرة",
            previous,
            re.I,
        )
    )


def _issue_from_history(history: Sequence[ChatTurn], message: str) -> str:
    candidates = [item.content.strip() for item in history if item.role == "user"]
    candidates.append(message.strip())
    for text in reversed(candidates):
        leftover = EMAIL_RE.sub("", text)
        leftover = PHONE_RE.sub("", leftover).strip(" ,.-")
        if len(leftover) >= 12:
            return text
    return message.strip()


def _business_profile_lines(business: Business) -> List[str]:
    lines = [f"Name: {business.name.strip()}"]
    description = (business.description or "").strip()
    if description:
        lines.append(f"Description: {description}")
    website = (business.website_url or "").strip()
    if website:
        lines.append(f"Website: {website}")
    email = (business.contact_email or "").strip()
    if email:
        lines.append(f"Email: {email}")
    phone = (business.contact_phone or "").strip()
    if phone:
        lines.append(f"Phone: {phone}")
    return lines


def _format_business_profile(business: Business) -> str:
    lines = _business_profile_lines(business)
    return "Business profile:\n" + "\n".join(lines)


def _log_chunk(item: dict) -> dict:
    meta = item.get("metadata") or {}
    text = str(meta.get("text") or "").strip().replace("\n", " ")
    return {
        "id": item.get("id"),
        "score": round(float(item.get("score") or 0), 4),
        "language": meta.get("language"),
        "document_title": meta.get("document_title"),
        "heading_path": meta.get("heading_path"),
        "retrieval_path": item.get("retrieval_path"),
        "snippet": text[:240],
    }


def _log_retrieval(**payload) -> None:
    if not get_settings().development_logs:
        return
    logger.info("retrieval %s", json.dumps(payload, ensure_ascii=False, default=str))
