from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from events.base import Event

INVENTORY_TOPIC = "inventory"


class ReservedItem(BaseModel):
    product_id: UUID
    quantity: int
    unit_price: Decimal


class StockReserved(Event):
    type: Literal["StockReserved"] = "StockReserved"
    items: list[ReservedItem]
    total: Decimal


class StockRejected(Event):
    type: Literal["StockRejected"] = "StockRejected"
    reason: str
