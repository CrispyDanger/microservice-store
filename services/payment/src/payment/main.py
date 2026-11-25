import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

from payment.api import health
from payment.cleaning import run_cleanup
from payment.consuming import run_consumer
from payment.db import TORTOISE_ORM
from payment.exceptions import register_exception_handlers
from payment.logs import configure_logging
from payment.publishing import run_relay


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with RegisterTortoise(app, config=TORTOISE_ORM):
        tasks = [
            asyncio.create_task(run_relay()),
            asyncio.create_task(run_consumer()),
            asyncio.create_task(run_cleanup()),
        ]
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="payment", lifespan=lifespan)

app.include_router(health.router)

register_exception_handlers(app)


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
