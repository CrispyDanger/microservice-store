import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from auth import AccessClaims, JWTAuth
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from events.orders import ORDERS_TOPIC, OrderCreated, OrderItem

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
# Only the PUBLIC key: this service can verify tokens but never create them.
# Read at import, so a missing key stops the service at startup, not on the first request.
JWT_PUBLIC_KEY = Path(os.getenv("JWT_PUBLIC_KEY_PATH", "/keys/public.pem")).read_text()

auth = JWTAuth(JWT_PUBLIC_KEY)
CurrentClaims = Annotated[AccessClaims, Depends(auth)]


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
async def place_order(body: PlaceOrder, request: Request, claims: CurrentClaims) -> dict:
    order_id = f"ord-{uuid4().hex[:8]}"
    # Build step 2: save the order as PENDING in this service's own database first.
    # user_id will be a plain UUID column there, not a foreign key: users live in another DB.
    event = OrderCreated(
        order_id=order_id, user_id=claims.user_id, items=body.items, total=body.total
    )
    key, value = event.to_kafka()
    await request.app.state.producer.send_and_wait(ORDERS_TOPIC, key=key, value=value)
    return {"order_id": order_id, "user_id": str(claims.user_id), "status": "PENDING"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
