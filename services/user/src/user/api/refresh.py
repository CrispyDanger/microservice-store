from fastapi import APIRouter

from user.schemas.auth import RefreshInput, TokenPair
from user.services.refresh import refresh_tokens

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshInput):
    return await refresh_tokens(body.refresh_token)
