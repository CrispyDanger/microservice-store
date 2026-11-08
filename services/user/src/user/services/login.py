from user.exceptions import InvalidCredentials
from user.models import User
from user.schemas.auth import LoginInput, TokenPair
from user.security.passwords import DUMMY_HASH, verify_password
from user.services.tokens import issue_tokens


async def login_user(data: LoginInput) -> TokenPair:
    user = await User.get_or_none(email=data.email.lower())
    if user is None:
        verify_password(data.password, DUMMY_HASH)
        raise InvalidCredentials()
    if not verify_password(data.password, user.password) or not user.is_active:
        raise InvalidCredentials()
    return await issue_tokens(user)
