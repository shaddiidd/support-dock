from fastapi import APIRouter

from app.api.v1.endpoints import auth, businesses, chat, documents, tickets, widget

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(businesses.router)
api_router.include_router(documents.router)
api_router.include_router(tickets.router)
api_router.include_router(chat.router)
api_router.include_router(widget.router)
