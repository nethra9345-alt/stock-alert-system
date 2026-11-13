"""
Token Lifecycle Service (Stage 10.1 Hardening).
Provides refresh-token rotation, revocation, and replay-attack detection.
"""
import datetime
import logging
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    RefreshTokenData,
)
from backend.app.models.user import User, RefreshToken

logger = logging.getLogger("stockpulse.security.token")


def store_refresh_token(
    db: Session,
    user_id: int,
    token_data: RefreshTokenData
) -> RefreshToken:
    """Persists a new refresh token record in PostgreSQL."""
    db_token = RefreshToken(
        user_id=user_id,
        jti=token_data.jti,
        token_hash=hash_token(token_data.token),
        expires_at=token_data.expires_at,
        is_revoked=False,
        replaced_by=None,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def rotate_refresh_token(
    db: Session,
    refresh_token_str: str
) -> Tuple[str, RefreshTokenData, User]:
    """
    Validates, rotates and revokes an existing refresh token.
    Implements REPLAY ATTACK DETECTION:
    If a revoked or previously rotated token is presented again, all tokens
    belonging to that user are immediately revoked to protect the account.
    """
    try:
        payload = decode_token(refresh_token_str)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token signature.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected refresh token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id_str = payload.get("sub")
    jti = payload.get("jti")
    if not user_id_str or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims: missing subject or jti.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = int(user_id_str)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Lookup token record by jti or hash
    token_record = db.query(RefreshToken).filter(
        RefreshToken.jti == jti,
        RefreshToken.user_id == user_id
    ).first()

    # 1. REPLAY ATTACK DETECTION
    if token_record and (token_record.is_revoked or token_record.replaced_by is not None):
        logger.warning(
            f"SECURITY ALERT: Replay attack detected for user {user_id}. "
            f"Token jti={jti} was already rotated/revoked! Revoking all active tokens."
        )
        # Immediately invalidate all sessions for this user
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({RefreshToken.is_revoked: True})
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security alert: Refresh token has already been rotated. Session revoked for your protection.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not token_record:
        # Fallback query by token hash (e.g. if jti was absent)
        token_hash = hash_token(refresh_token_str)
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id
        ).first()

    if not token_record or token_record.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or is invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check expiration in database
    if token_record.expires_at < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):
        token_record.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 2. Issue NEW rotated refresh token & short-lived access token
    new_token_data = create_refresh_token(subject=user.id)
    new_access_token = create_access_token(subject=user.id)

    # 3. Mark old token as revoked and link replaced_by to new jti
    token_record.is_revoked = True
    token_record.replaced_by = new_token_data.jti

    # 4. Persist new refresh token record
    new_record = RefreshToken(
        user_id=user.id,
        jti=new_token_data.jti,
        token_hash=hash_token(new_token_data.token),
        expires_at=new_token_data.expires_at,
        is_revoked=False,
        replaced_by=None
    )
    db.add(new_record)
    db.commit()

    return new_access_token, new_token_data, user


def revoke_refresh_token(
    db: Session,
    refresh_token_str: str
) -> bool:
    """Revokes a specific refresh token in the database upon logout."""
    try:
        payload = decode_token(refresh_token_str)
        jti = payload.get("jti")
        user_id = payload.get("sub")
        if jti and user_id:
            token_record = db.query(RefreshToken).filter(
                RefreshToken.jti == jti,
                RefreshToken.user_id == int(user_id)
            ).first()
            if token_record:
                token_record.is_revoked = True
                db.commit()
                return True
    except Exception:
        pass

    # Fallback by hash
    token_hash = hash_token(refresh_token_str)
    token_record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if token_record:
        token_record.is_revoked = True
        db.commit()
        return True

    return False


def revoke_all_user_tokens(
    db: Session,
    user_id: int
) -> int:
    """Revokes all refresh tokens for a user across all devices."""
    count = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).update({RefreshToken.is_revoked: True})
    db.commit()
    return count
