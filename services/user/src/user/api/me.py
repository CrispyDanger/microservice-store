from fastapi import APIRouter

from user.dependencies import CurrentUser
from user.schemas.user import UserOutput, UserUpdateInput
from user.services.me import update_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOutput)
async def get_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOutput)
async def update_me(body: UserUpdateInput, user: CurrentUser):
    return await update_profile(user, body)
