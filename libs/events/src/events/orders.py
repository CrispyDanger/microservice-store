from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field

from events.base import Event

ORDERS_TOPIC = "orders"


class OrderItem(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


class OrderCreated(Event):
    type: Literal["OrderCreated"] = "OrderCreated"
    items: list[OrderItem]
    total: Decimal


class OrderConfirmed(Event):
    type: Literal["OrderConfirmed"] = "OrderConfirmed"


class OrderCancelled(Event):
    type: Literal["OrderCancelled"] = "OrderCancelled"
    reason: str
