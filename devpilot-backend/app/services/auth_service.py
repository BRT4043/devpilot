"""GitHub OAuth exchange, token encryption, and JWT handling."""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.models import User

settings = get_settings()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


# --- GitHub token encryption (at rest) ---

def _fernet() -> Fernet:
    return Fernet(settings.token_encryption_key.encode())


def encrypt_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_token(enc: str) -> str:
    return _fernet().decrypt(enc.encode()).decode()


# --- Our own JWT ---

def create_jwt(user_id: uuid.UUID) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


# --- OAuth flow ---

def github_login_url() -> str:
    params = urlencode({
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_callback_url,
        "scope": "repo read:user user:email",
    })
    return f"{GITHUB_AUTHORIZE_URL}?{params}"


async def exchange_code_for_token(code: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_callback_url,
            },
        )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError(f"GitHub OAuth failed: {data.get('error_description', data)}")
    return token


async def fetch_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
    resp.raise_for_status()
    return resp.json()


async def upsert_user(db: AsyncSession, gh_user: dict, access_token: str) -> User:
    result = await db.execute(select(User).where(User.github_id == gh_user["id"]))
    user = result.scalar_one_or_none()

    enc = encrypt_token(access_token)
    if user is None:
        user = User(
            github_id=gh_user["id"],
            username=gh_user["login"],
            avatar_url=gh_user.get("avatar_url"),
            email=gh_user.get("email"),
            github_token_enc=enc,
        )
        db.add(user)
    else:
        user.username = gh_user["login"]
        user.avatar_url = gh_user.get("avatar_url")
        user.github_token_enc = enc  # refresh token on every login

    await db.commit()
    await db.refresh(user)
    return user
