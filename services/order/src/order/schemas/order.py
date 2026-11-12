from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from events.orders import OrderItem as OrderItemInput
from order.models import OrderStatus


class PlaceOrderInput(BaseModel):
    items: list[OrderItemInput] = Field(min_length=1)
    total: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("items")
    @classmethod
    def one_line_per_product(cls, items: list[OrderItemInput]) -> list[OrderItemInput]:
        product_ids = [item.product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("each product may appear only once; combine the quantities")
        return items


class OrderItemOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: UUID
    quantity: int


class OrderOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    status: OrderStatus
    total: Decimal
    cancel_reason: str | None
    items: list[OrderItemOutput]
    created_at: datetime
