import asyncio
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

from order.api import cancel_order, get_order, health, list_orders, place_order
from order.db import TORTOISE_ORM
from order.exceptions import register_exception_handlers
from order.publishing import run_relay


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RegisterTortoise(app, config=TORTOISE_ORM):
        relay = asyncio.create_task(run_relay())
        try:
            yield
        finally:
            relay.cancel()
            with suppress(asyncio.CancelledError):
                await relay


app = FastAPI(title="order", lifespan=lifespan)

app.include_router(health.router)
app.include_router(place_order.router)
app.include_router(get_order.router)
app.include_router(list_orders.router)
app.include_router(cancel_order.router)

register_exception_handlers(app)


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
