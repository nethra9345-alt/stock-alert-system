import bcrypt
import hashlib
import jwt
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union, NamedTuple
from backend.app.core.config import settings


class RefreshTokenData(NamedTuple):
    token: str
    jti: str
    expires_at: datetime

    def __str__(self) -> str:
        return self.token


def hash_token(token: str) -> str:
    """Returns SHA-256 digest of token for indexing and fast constant-time lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generates a cryptographically strong 256-bit hexadecimal CSRF anti-forgery token."""
    return secrets.token_hex(32)


def hash_password(password: str) -> str:
    """Hashes a plain-text password using salt-generated bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verifies a plain-text password against a stored bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Creates a cryptographically signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access"
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, int],
    jti: Optional[str] = None
) -> RefreshTokenData:
    """
    Creates a cryptographically signed long-lived refresh token with unique jti.
    Returns a RefreshTokenData(token, jti, expires_at) which can be used as a string
    or unpacked.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token_jti = jti or str(uuid.uuid4())

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "jti": token_jti,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh"
    }

    token = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return RefreshTokenData(token=token, jti=token_jti, expires_at=expire)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and cryptographically validates a JWT token.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )

