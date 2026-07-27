"""JWT issuing/verification and encryption of GitHub tokens at rest."""

from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def create_access_token(user_id: str, minutes: int | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=minutes or settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_state_token() -> str:
    """Short-lived signed token used as the OAuth `state` param (CSRF protection)."""
    expire = datetime.now(UTC) + timedelta(minutes=10)
    return jwt.encode({"exp": expire, "type": "state"}, settings.jwt_secret, algorithm=ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> dict | None:
    """Returns the payload if valid and of the expected type, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def _fernet() -> Fernet:
    return Fernet(settings.token_encryption_key.encode())


def encrypt_github_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_github_token(enc: str) -> str:
    return _fernet().decrypt(enc.encode()).decode()
