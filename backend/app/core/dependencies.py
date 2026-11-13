"""
Authentication & Data Isolation Dependencies (Stage 10 Production Ready).
Provides JWT Bearer validation, password hashing integration, and backwards-compatible
isolation for existing test suites.
"""
from typing import Optional
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import decode_token, hash_password
from backend.app.models.user import User

DEFAULT_USER_EMAIL = "trader@stockpulse.ai"
DEFAULT_USERNAME = "trader_pro"


def get_or_create_default_user(db: Session) -> Optional[User]:
    """Ensures a default primary user exists in the database for local dev and testing."""
    if not settings.is_demo_allowed:
        return None

    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            id=1,
            email=DEFAULT_USER_EMAIL,
            username=DEFAULT_USERNAME,
            hashed_password=hash_password("TraderPass@2026"),
            full_name="Pro Market Trader",
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.hashed_password:
        user.hashed_password = hash_password("TraderPass@2026")
        db.commit()
    return user


def get_current_user(
    authorization: Optional[str] = Header(None, description="Standard Bearer <jwt> authorization header"),
    x_user_id: Optional[int] = Header(None, description="Legacy header - rejected in production"),
    db: Session = Depends(get_db)
) -> User:
    """
    Returns the authenticated user.
    1. If 'Authorization: Bearer <token>' is provided, cryptographically verifies the JWT.
    2. If invalid/expired token is supplied, raises 401 Unauthorized.
    3. If 'X-User-Id' header is provided:
       - REJECTED with 401 Unauthorized if in production or legacy auth disabled.
       - Allowed only in test/development environments where legacy header auth is explicitly enabled.
    4. If no authentication is provided:
       - REJECTED with 401 Unauthorized if in production or fallback disabled.
       - Defaults to User ID 1 only in development/test environments.
    """
    get_or_create_default_user(db)

    # 1. Reject header identity spoofing in production
    if x_user_id is not None and not settings.is_legacy_auth_allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header-based user identity spoofing (X-User-Id) is rejected. Cryptographic Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 2. Cryptographic JWT Bearer Authentication (Highest Priority)
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"}
            )
        token = authorization[len("Bearer "):].strip()
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload: missing subject identifier",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User associated with token not found or deactivated",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return user
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token has expired. Please refresh your session.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: invalid token signature",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # 3. Legacy X-User-Id Header Isolation (For Stage 1-9 Regression Tests in non-production)
    if x_user_id is not None and settings.is_legacy_auth_allowed:
        user = db.query(User).filter(User.id == x_user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User with ID {x_user_id} does not exist or is inactive"
            )
        return user

    # 4. Anonymous fallback guard
    if not settings.is_fallback_allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: Cryptographic Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 5. Default fallback for development/test convenience
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_jwt_user(
    authorization: str = Header(..., description="Required Bearer <jwt> authorization header"),
    db: Session = Depends(get_db)
) -> User:
    """
    Strict JWT authentication dependency with zero fallback.
    Used for sensitive protected endpoints requiring verified cryptographic credentials.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'Bearer '",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token = authorization[len("Bearer "):].strip()
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Validates that current authenticated user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user
