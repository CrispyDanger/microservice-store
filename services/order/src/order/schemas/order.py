from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from events.orders import OrderItem


class PlaceOrderInput(BaseModel):
    items: list[OrderItem]
    total: Decimal


class PlaceOrderOutput(BaseModel):
    order_id: str
    user_id: UUID
    status: str
