import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.cors import OriginAwareCORSMiddleware
from app.db.base import Base
from app.db.session import engine
from app.models import Business, Document, Ticket, User  # noqa: F401

logger = logging.getLogger(__name__)


def _ensure_schema() -> None:
    statements = [
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS knowledge_languages JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS languages JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS support_email VARCHAR(255)",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255)",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(40)",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS assistant_instructions TEXT",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS website_url VARCHAR(500)",
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS website_origin VARCHAR(255)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_businesses_website_origin ON businesses (website_origin)",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS customer_email VARCHAR(255)",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(40)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_schema()
    except Exception as exc:
        logger.warning(
            "Database is not ready (%s). Set DATABASE_URL in api/.env to your Neon URI.",
            exc,
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Support Dock API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        OriginAwareCORSMiddleware,
        dashboard_origins=settings.cors_origin_list,
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(OperationalError)
    async def database_unavailable(_: Request, __: OperationalError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Database is unavailable. Check DATABASE_URL in api/.env."},
        )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
