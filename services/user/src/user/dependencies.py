from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from user.exceptions import Forbidden, InvalidToken
from user.models import Role, User
from user.security.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise InvalidToken()
    claims = decode_access_token(creds.credentials)
    user = await User.get_or_none(id=claims.user_id)
    if user is None or not user.is_active:
        raise InvalidToken()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(role: Role):
    async def checker(user: CurrentUser) -> User:
        if user.role != role:
            raise Forbidden()
        return user
    return checker
