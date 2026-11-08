from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.tokens import AccessClaims, InvalidToken, decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


class JWTAuth:
    """FastAPI dependency that authenticates a request from its access token alone.

    No database and no call to the user service: the signature proves the user service
    issued the token. Usage:

        auth = JWTAuth(public_key)
        CurrentClaims = Annotated[AccessClaims, Depends(auth)]
    """

    def __init__(self, public_key: str) -> None:
        self.public_key = public_key

    async def __call__(
        self,
        creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    ) -> AccessClaims:
        if creds is None:
            raise _unauthorized()
        try:
            return decode_access_token(creds.credentials, self.public_key)
        except InvalidToken as exc:
            raise _unauthorized() from exc

    def require_role(self, role: str):
        async def checker(claims: Annotated[AccessClaims, Depends(self)]) -> AccessClaims:
            if claims.role != role:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions")
            return claims

        return checker
