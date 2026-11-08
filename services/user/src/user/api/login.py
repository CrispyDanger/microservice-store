from fastapi import APIRouter

from user.schemas.auth import LoginInput, TokenPair
from user.services.login import login_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(body: LoginInput):
    return await login_user(body)
