"""
Authentication & Data Isolation Dependencies.

SECURITY AUDIT NOTE (STAGE 6 COMPLIANCE):
-----------------------------------------
The current `X-User-Id` HTTP header-based authentication is designed strictly for local
development, sandboxed prototyping, and multi-tenant test suites.
CRITICAL LIMITATIONS:
1. It is spoofable by any HTTP client that can send custom headers.
2. It lacks cryptographic signatures, expiration timestamps, or token revocation.
3. In a public production deployment, malicious actors could access or mutate other users'
   portfolios, price alerts, and transactions simply by changing the `X-User-Id` integer.

REQUIRED PRODUCTION UPGRADE PATH:
---------------------------------
1. JSON Web Token (JWT) Bearer Authentication (RFC 7519) using HS256/RS256.
2. An `/api/auth/login` endpoint issuing signed access tokens with short TTL (e.g. 15-30m)
   and HTTP-only secure refresh tokens.
3. Dependency `OAuth2PasswordBearer` validating cryptographic signature, issuer, and expiry.
4. Extracting `user_id` strictly from the verified JWT claims (`sub` field).
"""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User

DEFAULT_USER_EMAIL = "trader@stockpulse.ai"
DEFAULT_USERNAME = "trader_pro"


def get_or_create_default_user(db: Session) -> User:
    """Ensures a default primary user exists in the database for local dev and testing."""
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            id=1,
            email=DEFAULT_USER_EMAIL,
            username=DEFAULT_USERNAME,
            full_name="Pro Market Trader",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    x_user_id: Optional[int] = Header(None, description="Header for user identification and multi-tenant isolation"),
    db: Session = Depends(get_db)
) -> User:
    """
    Returns the authenticated user for request data isolation.
    If X-User-Id is provided, returns that user.
    Otherwise defaults to the primary default user (ID 1).
    """
    get_or_create_default_user(db)

    if x_user_id is not None:
        user = db.query(User).filter(User.id == x_user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User with ID {x_user_id} does not exist or is inactive"
            )
        return user

    user = db.query(User).filter(User.id == 1).first()
    return user

