from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_owned_business
from app.db.session import get_db
from app.models.business import Business
from app.schemas.ticket import TicketPublic
from app.services.ticket import get_ticket, list_tickets

router = APIRouter(prefix="/businesses/{business_id}/tickets", tags=["tickets"])


@router.get("", response_model=List[TicketPublic])
def read_tickets(
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
) -> List:
    return list_tickets(db, business.id)


@router.get("/{ticket_id}", response_model=TicketPublic)
def read_ticket(
    ticket_id: UUID,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
):
    ticket = get_ticket(db, business.id, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket
