from datetime import UTC, datetime, timedelta

from user.config import settings
from user.models import RefreshToken, User
from user.schemas.auth import TokenPair
from user.security.tokens import create_access_token, new_refresh_token


async def issue_tokens(user: User) -> TokenPair:
    raw, token_hash = new_refresh_token()
    await RefreshToken.create(
        user=user,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
    )
    return TokenPair(access_token=create_access_token(user), refresh_token=raw)
