from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path
import secrets

import auth
import jwt
from auth import ACCESS_TOKEN_TYPE, ALGORITHM, AccessClaims

from user.config import settings
from user.exceptions import InvalidToken
from user.models import User

_PRIVATE_KEY = Path(settings.jwt_private_key_path).read_text()
_PUBLIC_KEY = Path(settings.jwt_public_key_path).read_text()


def create_access_token(user: User) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": str(user.role),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> AccessClaims:
    # Verification lives in libs/auth, shared with every other service; here we only
    # translate the lib's error into this service's InvalidToken (same JSON error format)
    try:
        return auth.decode_access_token(token, _PUBLIC_KEY)
    except auth.InvalidToken as exc:
        raise InvalidToken() from exc


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)
