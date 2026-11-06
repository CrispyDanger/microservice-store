import os
from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, Request
from pydantic import BaseModel

from events.orders import ORDERS_TOPIC, OrderCreated, OrderItem

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    app.state.producer = producer
    try:
        yield
    finally:
        await producer.stop()


app = FastAPI(title="order", lifespan=lifespan)


class PlaceOrder(BaseModel):
    items: list[OrderItem]
    total: Decimal


@app.post("/orders", status_code=202)
async def place_order(body: PlaceOrder, request: Request) -> dict:
    order_id = f"ord-{uuid4().hex[:8]}"
    # Build step 2: save the order as PENDING in this service's own database first.
    event = OrderCreated(order_id=order_id, items=body.items, total=body.total)
    key, value = event.to_kafka()
    await request.app.state.producer.send_and_wait(ORDERS_TOPIC, key=key, value=value)
    return {"order_id": order_id, "status": "PENDING"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
