import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

from inventory.api import create_product, get_product, health, list_products, restock_product
from inventory.cleaning import run_cleanup
from inventory.consuming import run_consumer
from inventory.db import TORTOISE_ORM
from inventory.exceptions import register_exception_handlers
from inventory.logs import configure_logging
from inventory.publishing import run_relay


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


app = FastAPI(title="inventory", lifespan=lifespan)

app.include_router(health.router)
app.include_router(list_products.router)
app.include_router(get_product.router)
app.include_router(create_product.router)
app.include_router(restock_product.router)

register_exception_handlers(app)


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
