from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import jwt

# Shared with the issuer (user service), so both sides agree on the token format
ALGORITHM = "RS256"
ACCESS_TOKEN_TYPE = "access"


class InvalidToken(Exception):
    """The token is malformed, forged, expired or not an access token."""


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: UUID
    role: str
    expires_at: datetime


def decode_access_token(token: str, public_key: str) -> AccessClaims:
    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[ALGORITHM],  # never trust the token's own "alg" header
            options={"require": ["exp", "sub", "type", "role"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc

    if claims["type"] != ACCESS_TOKEN_TYPE:
        raise InvalidToken("not an access token")
    try:
        user_id = UUID(claims["sub"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidToken("sub is not a UUID") from exc

    return AccessClaims(
        user_id=user_id,
        role=str(claims["role"]),
        expires_at=datetime.fromtimestamp(claims["exp"], UTC),
    )
