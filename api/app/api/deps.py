from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.origins import origins_match
from app.core.security import CREDENTIALS_EXCEPTION, decode_access_token
from app.db.session import get_db
from app.models.business import Business
from app.models.user import User
from app.services.auth import get_user_by_id
from app.services.business import get_business, get_business_for_owner

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise CREDENTIALS_EXCEPTION

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if not subject:
        raise CREDENTIALS_EXCEPTION

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise CREDENTIALS_EXCEPTION from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise CREDENTIALS_EXCEPTION

    return user


def get_owned_business(
    business_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Business:
    business = get_business_for_owner(db, current_user.id, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


def get_widget_business(
    business_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> Business:
    business = get_business(db, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    origin = request.headers.get("origin")
    if not business.website_origin or not origins_match(origin, business.website_origin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat is only allowed from this business's website.",
        )
    return business
