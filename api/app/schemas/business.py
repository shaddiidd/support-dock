from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.origins import WebsiteUrlError, normalize_website_url


def _empty_to_none(value):
    if value == "":
        return None
    return value


def _parse_website_url(value):
    cleaned = _empty_to_none(value)
    if cleaned is None:
        return None
    try:
        return normalize_website_url(str(cleaned))
    except WebsiteUrlError as exc:
        raise ValueError(str(exc)) from exc


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    website_url: str = Field(min_length=1, max_length=500)
    support_email: Optional[EmailStr] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(default=None, max_length=40)
    assistant_instructions: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("website_url", mode="before")
    @classmethod
    def require_website(cls, value):
        parsed = _parse_website_url(value)
        if parsed is None:
            raise ValueError("Enter a website URL, such as https://example.com")
        return parsed

    @field_validator("support_email", "contact_email", "contact_phone", "assistant_instructions", mode="before")
    @classmethod
    def empty_optional(cls, value):
        return _empty_to_none(value)


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    website_url: Optional[str] = Field(default=None, max_length=500)
    support_email: Optional[EmailStr] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(default=None, max_length=40)
    assistant_instructions: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("website_url", mode="before")
    @classmethod
    def parse_website(cls, value):
        return _parse_website_url(value)

    @field_validator("support_email", "contact_email", "contact_phone", "assistant_instructions", mode="before")
    @classmethod
    def empty_optional(cls, value):
        return _empty_to_none(value)


class BusinessPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    website_url: Optional[str] = None
    website_origin: Optional[str] = None
    support_email: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    assistant_instructions: Optional[str] = None
    knowledge_languages: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    widget_url: Optional[str] = None


def as_public(business, request) -> BusinessPublic:
    from app.core.config import get_settings
    from app.core.origins import widget_chat_url

    return BusinessPublic.model_validate(business).model_copy(
        update={
            "widget_url": widget_chat_url(
                request,
                business.id,
                get_settings().public_api_url,
            )
        }
    )
