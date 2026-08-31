from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

WIDGET_CHAT_PATH = re.compile(
    r"^/api/v1/widget/"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
    r"/chat/?$"
)


class WebsiteUrlError(ValueError):
    pass


def normalize_website_url(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise WebsiteUrlError("Enter a website URL.")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        text = f"https://{text}"

    parts = urlsplit(text)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise WebsiteUrlError("Website URL must start with http:// or https://")
    if not parts.hostname or "@" in parts.netloc:
        raise WebsiteUrlError("Enter a valid website URL, such as https://example.com")

    path = parts.path if parts.path and parts.path != "/" else ""
    return urlunsplit((scheme, parts.netloc.lower(), path, "", ""))


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def origins_match(left: Optional[str], right: Optional[str]) -> bool:
    if not left or not right:
        return False
    return left.rstrip("/").lower() == right.rstrip("/").lower()


def public_api_base(request, configured: str = "") -> str:
    text = (configured or "").strip().rstrip("/")
    if text:
        return text
    return str(request.base_url).rstrip("/")


def widget_chat_url(request, business_id: UUID, configured: str = "") -> str:
    return f"{public_api_base(request, configured)}/api/v1/widget/{business_id}/chat"


def widget_business_id(path: str) -> Optional[UUID]:
    match = WIDGET_CHAT_PATH.match(path or "")
    if not match:
        return None
    try:
        return UUID(match.group(1))
    except ValueError:
        return None
