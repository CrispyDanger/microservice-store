import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

from user.exceptions import register_exception_handlers
from user.api import change_password, get_user, health, login, me, register
from user.db import TORTOISE_ORM


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RegisterTortoise(app, config=TORTOISE_ORM):
        yield


app = FastAPI(lifespan=lifespan)


app.include_router(health.router)
app.include_router(register.router)
app.include_router(login.router)
app.include_router(me.router)
app.include_router(change_password.router)
app.include_router(get_user.router)

register_exception_handlers(app)


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8001)
