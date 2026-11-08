from fastapi import APIRouter

from user.services.register import register_user

from user.schemas.user import RegisterInput, UserOutput


router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=UserOutput, status_code=201)
async def register(body: RegisterInput):
    return await register_user(body)
