from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

from inventory.api import create_product, get_product, health, list_products, restock_product
from inventory.db import TORTOISE_ORM
from inventory.exceptions import register_exception_handlers
from inventory.logs import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with RegisterTortoise(app, config=TORTOISE_ORM):
        yield


app = FastAPI(title="inventory", lifespan=lifespan)

app.include_router(health.router)
app.include_router(list_products.router)
app.include_router(get_product.router)
app.include_router(create_product.router)
app.include_router(restock_product.router)

register_exception_handlers(app)


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
