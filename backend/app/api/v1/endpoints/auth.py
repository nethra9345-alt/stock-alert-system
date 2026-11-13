import time
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
)
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse
)
from backend.app.core.rate_limit import auth_rate_limiter
from backend.app.services.token_service import (
    store_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
)

router = APIRouter()


def check_auth_rate_limit(client_ip: str):
    """Enforces multi-worker safe rate limiting on sensitive authentication endpoints."""
    auth_rate_limiter.check(client_ip)


def set_auth_cookies(
    response: Response,
    request: Request,
    refresh_token: str,
    csrf_token: Optional[str] = None
) -> str:
    """Sets HttpOnly, SameSite, Secure refresh cookie and companion CSRF cookie."""
    is_secure = settings.SECURE_COOKIES or settings.is_production or request.url.scheme == "https"
    csrf_val = csrf_token or generate_csrf_token()

    # 1. HttpOnly Refresh Token Cookie (strictly inaccessible to JavaScript)
    response.set_cookie(
        key="stockpulse_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth"
    )

    # 2. Non-HttpOnly CSRF anti-forgery cookie (readable by frontend for double-submit header)
    response.set_cookie(
        key="stockpulse_csrf_token",
        value=csrf_val,
        httponly=False,
        secure=is_secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/"
    )
    return csrf_val


def clear_auth_cookies(response: Response, request: Request):
    """Clears refresh and CSRF cookies on logout."""
    is_secure = settings.SECURE_COOKIES or settings.is_production or request.url.scheme == "https"
    response.delete_cookie(key="stockpulse_refresh_token", path="/api/auth", httponly=True, secure=is_secure, samesite="lax")
    response.delete_cookie(key="stockpulse_csrf_token", path="/", httponly=False, secure=is_secure, samesite="lax")


def verify_csrf_if_cookie_auth(request: Request):
    """
    Validates Double Submit CSRF token when request uses cookie authentication.
    'X-CSRF-Token' header must match the 'stockpulse_csrf_token' cookie to prevent cross-site request forgery.
    """
    if settings.CSRF_PROTECTION_ENABLED:
        csrf_header = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get("stockpulse_csrf_token")
        if not csrf_header or not csrf_cookie or not secrets.compare_digest(csrf_header, csrf_cookie):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed. Missing or invalid X-CSRF-Token header.",
            )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    req: Request,
    resp: Response,
    user_in: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Registers a new user account with bcrypt password hashing, issues signed JWT tokens,
    persists refresh token in PostgreSQL, and sets HttpOnly SameSite cookies.
    """
    client_ip = req.client.host if req.client else "unknown"
    check_auth_rate_limit(client_ip)

    # 1. Check if email or username already taken
    existing_user = db.query(User).filter(
        or_(User.email == user_in.email.lower(), User.username == user_in.username.lower())
    ).first()

    if existing_user:
        if existing_user.email.lower() == user_in.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username already exists."
        )

    # 2. Hash password & persist user
    new_user = User(
        email=user_in.email.lower(),
        username=user_in.username.lower(),
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        is_active=True,
        is_superuser=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. Generate access and refresh tokens
    access_token = create_access_token(subject=new_user.id)
    refresh_token_data = create_refresh_token(subject=new_user.id)

    # 4. Persist refresh token in database for rotation & revocation tracking
    store_refresh_token(db=db, user_id=new_user.id, token_data=refresh_token_data)

    # 5. Set HttpOnly, SameSite, Secure cookie & CSRF cookie
    csrf_token = set_auth_cookies(response=resp, request=req, refresh_token=refresh_token_data.token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_data.token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(new_user),
        csrf_token=csrf_token
    )


@router.post("/login", response_model=TokenResponse)
def login_user(
    req: Request,
    resp: Response,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials, blocks demo account usage in production,
    issues cryptographic JWT access and refresh tokens, and attaches HttpOnly cookies.
    """
    client_ip = req.client.host if req.client else "unknown"
    check_auth_rate_limit(client_ip)

    identifier = credentials.username_or_email.strip().lower()

    # Demo Account Production Guard
    is_demo_identifier = identifier in ("trader_pro", "trader@stockpulse.ai")
    if is_demo_identifier and not settings.is_demo_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo account login is disabled in production environment."
        )

    # Query by username or email
    user = db.query(User).filter(
        or_(User.email == identifier, User.username == identifier)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your email/username and password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated. Please contact system administrator."
        )

    access_token = create_access_token(subject=user.id)
    refresh_token_data = create_refresh_token(subject=user.id)

    # Persist in DB
    store_refresh_token(db=db, user_id=user.id, token_data=refresh_token_data)

    # Set HttpOnly & CSRF cookies
    csrf_token = set_auth_cookies(response=resp, request=req, refresh_token=refresh_token_data.token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_data.token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        csrf_token=csrf_token
    )


@router.post("/refresh", response_model=Dict[str, Any])
def refresh_access_token(
    req: Request,
    resp: Response,
    refresh_req: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Exchanges an active refresh token for a newly issued access token and rotated refresh token.
    Supports HttpOnly cookie extraction with CSRF validation, or JSON body fallback.
    Performs automatic token rotation and replay-attack detection.
    """
    # 1. Determine refresh token from HttpOnly cookie or request body
    cookie_token = req.cookies.get("stockpulse_refresh_token")
    body_token = refresh_req.refresh_token if (refresh_req and refresh_req.refresh_token) else None

    # If relying on cookie-based authentication, enforce CSRF protection
    if not body_token and cookie_token:
        verify_csrf_if_cookie_auth(req)
        refresh_token_str = cookie_token
    elif body_token:
        refresh_token_str = body_token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 3. Rotate refresh token in database (includes replay attack detection)
    new_access_token, new_refresh_data, user = rotate_refresh_token(
        db=db,
        refresh_token_str=refresh_token_str
    )

    # 4. Set rotated HttpOnly cookie & new CSRF token
    csrf_token = set_auth_cookies(response=resp, request=req, refresh_token=new_refresh_data.token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_data.token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "csrf_token": csrf_token
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Returns profile details for the currently authenticated user session.
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout_user(
    req: Request,
    resp: Response,
    refresh_req: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Invalidates user session by revoking the refresh token in PostgreSQL
    and clearing all authentication cookies.
    """
    body_token = refresh_req.refresh_token if (refresh_req and refresh_req.refresh_token) else None
    cookie_token = req.cookies.get("stockpulse_refresh_token")

    if not body_token and cookie_token:
        verify_csrf_if_cookie_auth(req)
        token_str = cookie_token
    else:
        token_str = body_token

    if token_str:
        revoke_refresh_token(db=db, refresh_token_str=token_str)

    clear_auth_cookies(response=resp, request=req)

    return {"status": "success", "message": "Successfully logged out. Refresh token revoked and session cookies cleared."}
