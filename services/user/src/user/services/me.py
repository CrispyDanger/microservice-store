from user.models import User
from user.schemas.user import UserUpdateInput


async def update_profile(user: User, data: UserUpdateInput) -> User:
    changes = data.model_dump(exclude_unset=True)
    if changes:
        user.update_from_dict(changes)
        await user.save(update_fields=list(changes))
    return user
