from datetime import UTC, datetime

from user.exceptions import InvalidCredentials
from user.models import RefreshToken, User
from user.schemas.user import ChangePasswordInput
from user.security.passwords import hash_password, verify_password


async def change_password(user: User, data: ChangePasswordInput) -> None:
    if not verify_password(data.old_password, user.password):
        raise InvalidCredentials()
    user.password = hash_password(data.new_password)
    await user.save(update_fields=["password"])
    # Log out every session: anyone else who knew the old password loses access
    await RefreshToken.filter(user=user, revoked_at=None).update(revoked_at=datetime.now(UTC))
