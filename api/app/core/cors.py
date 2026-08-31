from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.origins import origins_match, widget_business_id


class OriginAwareCORSMiddleware:
    """Allow the dashboard origins everywhere, and a business website only on its widget chat."""

    def __init__(self, app: ASGIApp, dashboard_origins: Sequence[str]) -> None:
        self.app = app
        self.dashboard_origins = {
            origin.strip().rstrip("/")
            for origin in dashboard_origins
            if origin and origin.strip()
        }
        self.allow_methods = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
        self.allow_headers = (
            "Accept, Accept-Language, Authorization, Content-Language, Content-Type"
        )
        self.max_age = "600"

    def origin_allowed(self, origin: str, path: str) -> bool:
        if any(origins_match(origin, allowed) for allowed in self.dashboard_origins):
            return True
        business_id = widget_business_id(path)
        if business_id is None:
            return False
        expected = _website_origin_for(business_id)
        return origins_match(origin, expected)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origin = headers.get("origin")
        if origin is None:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        allowed = self.origin_allowed(origin, path)

        if scope["method"] == "OPTIONS" and "access-control-request-method" in headers:
            response = self._preflight(headers, origin, allowed)
            await response(scope, receive, send)
            return

        async def send_with_cors(message: Message) -> None:
            if message["type"] == "http.response.start" and allowed:
                message.setdefault("headers", [])
                response_headers = MutableHeaders(scope=message)
                response_headers["Access-Control-Allow-Origin"] = origin
                response_headers["Access-Control-Allow-Credentials"] = "true"
                response_headers.add_vary_header("Origin")
            await send(message)

        await self.app(scope, receive, send_with_cors)

    def _preflight(self, request_headers: Headers, origin: str, allowed: bool) -> PlainTextResponse:
        headers = {
            "Access-Control-Allow-Methods": self.allow_methods,
            "Access-Control-Allow-Headers": request_headers.get(
                "access-control-request-headers"
            )
            or self.allow_headers,
            "Access-Control-Max-Age": self.max_age,
            "Vary": "Origin",
        }
        if allowed:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            return PlainTextResponse("OK", status_code=200, headers=headers)
        return PlainTextResponse(
            "Disallowed CORS origin",
            status_code=400,
            headers=headers,
        )


def _website_origin_for(business_id: UUID) -> Optional[str]:
    from app.db.session import SessionLocal
    from app.models.business import Business

    db = SessionLocal()
    try:
        business = db.get(Business, business_id)
        return business.website_origin if business else None
    except Exception:
        return None
    finally:
        db.close()
