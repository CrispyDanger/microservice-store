from contextlib import asynccontextmanager

import uvicorn
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI

from order.api import health, place_order
from order.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await producer.start()
    app.state.producer = producer
    try:
        yield
    finally:
        await producer.stop()


app = FastAPI(title="order", lifespan=lifespan)

app.include_router(health.router)
app.include_router(place_order.router)


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
