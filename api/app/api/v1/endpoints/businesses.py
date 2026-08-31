from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_business
from app.db.session import get_db
from app.models.business import Business
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessPublic, BusinessUpdate, as_public
from app.services.business import (
    WebsiteOriginTaken,
    create_business,
    delete_business,
    list_businesses,
    update_business,
)
from app.services.indexing import purge_business_knowledge

router = APIRouter(prefix="/businesses", tags=["businesses"])

DUPLICATE_NAME = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="You already have a business with this name",
)
WEBSITE_TAKEN = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Another business already uses this website",
)


def _conflict_from_integrity(exc: IntegrityError) -> HTTPException:
    message = str(getattr(exc, "orig", exc)).lower()
    if "website_origin" in message:
        return WEBSITE_TAKEN
    return DUPLICATE_NAME


@router.get("", response_model=List[BusinessPublic])
def read_businesses(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[BusinessPublic]:
    return [as_public(item, request) for item in list_businesses(db, current_user.id)]


@router.post("", response_model=BusinessPublic, status_code=status.HTTP_201_CREATED)
def create(
    payload: BusinessCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BusinessPublic:
    try:
        return as_public(create_business(db, current_user.id, payload), request)
    except WebsiteOriginTaken as exc:
        raise WEBSITE_TAKEN from exc
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc


@router.get("/{business_id}", response_model=BusinessPublic)
def read_business(
    request: Request,
    business: Business = Depends(get_owned_business),
) -> BusinessPublic:
    return as_public(business, request)


@router.patch("/{business_id}", response_model=BusinessPublic)
def update(
    payload: BusinessUpdate,
    request: Request,
    db: Session = Depends(get_db),
    business: Business = Depends(get_owned_business),
) -> BusinessPublic:
    try:
        return as_public(update_business(db, business, payload), request)
    except WebsiteOriginTaken as exc:
        raise WEBSITE_TAKEN from exc
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    db: Session = Depends(get_db),
    business: Business = Depends(get_owned_business),
) -> None:
    purge_business_knowledge(business.id)
    delete_business(db, business)
