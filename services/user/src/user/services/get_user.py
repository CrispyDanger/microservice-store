from uuid import UUID

from user.exceptions import UserNotFound
from user.models import User


async def get_user_by_id(user_id: UUID) -> User:
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise UserNotFound()
    return user
