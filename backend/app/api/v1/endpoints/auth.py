import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from backend.app.core.dependencies import get_current_user, require_jwt_user
from backend.app.models.user import User
from backend.app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse
)

router = APIRouter()

# In-memory rate limiting tracker for auth attempts (prevents brute-force attacks)
_AUTH_RATE_LIMIT_STORE: Dict[str, list] = {}
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_LOGIN_ATTEMPTS = settings.AUTH_RATE_LIMIT_PER_MINUTE


def check_auth_rate_limit(client_ip: str):
    """Enforces rate limiting on sensitive authentication endpoints."""
    now = time.time()
    history = _AUTH_RATE_LIMIT_STORE.get(client_ip, [])
    # Keep only timestamps in window
    history = [t for t in history if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(history) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many authentication attempts. Please wait {RATE_LIMIT_WINDOW_SECONDS} seconds."
        )
    history.append(now)
    _AUTH_RATE_LIMIT_STORE[client_ip] = history


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    req: Request,
    user_in: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Registers a new user account with bcrypt password hashing and issues signed JWT tokens.
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
    refresh_token = create_refresh_token(subject=new_user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
def login_user(
    req: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials and issues cryptographic JWT access and refresh tokens.
    """
    client_ip = req.client.host if req.client else "unknown"
    check_auth_rate_limit(client_ip)

    identifier = credentials.username_or_email.strip().lower()

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
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=Dict[str, Any])
def refresh_access_token(
    refresh_req: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Exchanges a valid refresh token for a newly issued access token.
    """
    try:
        payload = decode_token(refresh_req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token"
            )

        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found"
            )

        new_access_token = create_access_token(subject=user.id)
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please sign in again."
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Returns profile details for the currently authenticated user session.
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout_user():
    """
    Client session logout invalidation signal.
    """
    return {"status": "success", "message": "Successfully logged out. Please clear client session tokens."}
