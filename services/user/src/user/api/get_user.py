from uuid import UUID

from fastapi import APIRouter, Depends

from user.dependencies import require_role
from user.models import Role
from user.schemas.user import UserOutput
from user.services.get_user import get_user_by_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/{user_id}",
    response_model=UserOutput,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_user(user_id: UUID):
    return await get_user_by_id(user_id)
