from fastapi import APIRouter

from user.dependencies import CurrentUser
from user.schemas.user import ChangePasswordInput
from user.services.change_password import change_password as change_password_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/password", status_code=204)
async def change_password(body: ChangePasswordInput, user: CurrentUser):
    await change_password_service(user, body)
