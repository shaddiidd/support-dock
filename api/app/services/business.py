from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.origins import origin_of
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessUpdate


class WebsiteOriginTaken(Exception):
    pass


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _apply_website(business: Business, website_url: Optional[str]) -> None:
    if website_url is None:
        business.website_url = None
        business.website_origin = None
        return
    business.website_url = website_url
    business.website_origin = origin_of(website_url)


def _assert_origin_free(
    db: Session,
    origin: Optional[str],
    exclude_id: Optional[UUID] = None,
) -> None:
    if not origin:
        return
    statement = select(Business.id).where(Business.website_origin == origin)
    if exclude_id is not None:
        statement = statement.where(Business.id != exclude_id)
    if db.scalar(statement) is not None:
        raise WebsiteOriginTaken()


def list_businesses(db: Session, owner_id: UUID) -> List[Business]:
    statement = (
        select(Business)
        .where(Business.owner_id == owner_id)
        .order_by(Business.name.asc())
    )
    return list(db.scalars(statement))


def get_business(db: Session, business_id: UUID) -> Optional[Business]:
    return db.get(Business, business_id)


def get_business_for_owner(
    db: Session,
    owner_id: UUID,
    business_id: UUID,
) -> Optional[Business]:
    statement = select(Business).where(
        Business.id == business_id,
        Business.owner_id == owner_id,
    )
    return db.scalar(statement)


def create_business(db: Session, owner_id: UUID, payload: BusinessCreate) -> Business:
    origin = origin_of(payload.website_url)
    _assert_origin_free(db, origin)
    business = Business(
        owner_id=owner_id,
        name=payload.name.strip(),
        description=_clean_text(payload.description),
        support_email=_clean_text(str(payload.support_email) if payload.support_email else None),
        contact_email=_clean_text(str(payload.contact_email) if payload.contact_email else None),
        contact_phone=_clean_text(payload.contact_phone),
        assistant_instructions=_clean_text(payload.assistant_instructions),
    )
    _apply_website(business, payload.website_url)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def update_business(db: Session, business: Business, payload: BusinessUpdate) -> Business:
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        business.name = data["name"].strip()
    if "description" in data:
        business.description = _clean_text(data["description"])
    if "website_url" in data:
        website_url = data["website_url"]
        origin = origin_of(website_url) if website_url else None
        _assert_origin_free(db, origin, exclude_id=business.id)
        _apply_website(business, website_url)
    if "support_email" in data:
        value = data["support_email"]
        business.support_email = _clean_text(str(value) if value else None)
    if "contact_email" in data:
        value = data["contact_email"]
        business.contact_email = _clean_text(str(value) if value else None)
    if "contact_phone" in data:
        business.contact_phone = _clean_text(data["contact_phone"])
    if "assistant_instructions" in data:
        business.assistant_instructions = _clean_text(data["assistant_instructions"])
    db.commit()
    db.refresh(business)
    return business


def delete_business(db: Session, business: Business) -> None:
    db.delete(business)
    db.commit()
