from fastapi import APIRouter

from user.schemas.auth import RefreshInput
from user.services.logout import logout_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout", status_code=204)
async def logout(body: RefreshInput):
    await logout_user(body.refresh_token)
