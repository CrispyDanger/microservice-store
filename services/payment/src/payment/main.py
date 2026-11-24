from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

from payment.api import health
from payment.db import TORTOISE_ORM
from payment.exceptions import register_exception_handlers
from payment.logs import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with RegisterTortoise(app, config=TORTOISE_ORM):
        yield


app = FastAPI(title="payment", lifespan=lifespan)

app.include_router(health.router)

register_exception_handlers(app)


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
