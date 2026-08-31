from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_owned_business
from app.db.session import get_db
from app.models.business import Business
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatError, answer_question

router = APIRouter(prefix="/businesses/{business_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        return answer_question(
            db,
            business,
            payload.message,
            payload.history,
            payload.conversation_id,
        )
    except ChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
