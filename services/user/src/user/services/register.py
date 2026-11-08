from tortoise.exceptions import IntegrityError

from user.exceptions import EmailTaken
from user.models import User
from user.schemas.user import RegisterInput
from user.security.passwords import hash_password


async def register_user(data: RegisterInput) -> User:
    email = data.email.lower()
    if await User.exists(email=email):
        raise EmailTaken()

    try:
        return await User.create(
            email=email,
            password=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
        )
    except IntegrityError:
        raise EmailTaken()
