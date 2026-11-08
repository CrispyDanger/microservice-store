from datetime import UTC, datetime

from tortoise.transactions import in_transaction

from user.exceptions import InvalidToken
from user.models import RefreshToken, User
from user.schemas.auth import TokenPair
from user.security.tokens import hash_refresh_token
from user.services.tokens import issue_tokens


async def refresh_tokens(raw_token: str) -> TokenPair:
    now = datetime.now(UTC)
    async with in_transaction():
        # FOR UPDATE locks the row: a second request with the same token waits here
        # until this transaction commits, then sees revoked_at already set.
        token = await (
            RefreshToken.filter(token_hash=hash_refresh_token(raw_token))
            .select_for_update()
            .first()
        )
        if token is None or token.expires_at <= now:
            raise InvalidToken()
        if token.revoked_at is None:
            token.revoked_at = now
            await token.save(update_fields=["revoked_at"])
            user = await User.get(id=token.user_id)
            if not user.is_active:
                raise InvalidToken()
            return await issue_tokens(user)

    # Only reached when the token was ALREADY revoked: someone is reusing it.
    # We can't tell the real user from a thief, so every session of this user dies.
    # This runs outside the transaction: raising inside it would roll the revocation back.
    await RefreshToken.filter(user_id=token.user_id, revoked_at=None).update(revoked_at=now)
    raise InvalidToken()
