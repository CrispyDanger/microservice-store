from datetime import UTC, datetime

from user.models import RefreshToken
from user.security.tokens import hash_refresh_token


async def logout_user(raw_token: str) -> None:
    # No error for unknown or already revoked tokens: logout reveals nothing and is safe to repeat
    await RefreshToken.filter(
        token_hash=hash_refresh_token(raw_token), revoked_at=None
    ).update(revoked_at=datetime.now(UTC))
