from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(default=0, ge=0, le=1_000_000)


class RestockInput(BaseModel):
    quantity: int = Field(gt=0, le=1_000_000)


class ProductOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    price: Decimal
    stock: int
    created_at: datetime
    updated_at: datetime


class ProductListOutput(BaseModel):
    products: list[ProductOutput]
    count: int
    limit: int
    offset: int
