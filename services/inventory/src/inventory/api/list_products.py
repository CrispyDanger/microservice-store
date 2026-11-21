from typing import Annotated

from fastapi import APIRouter, Query

from inventory.schemas.product import ProductListOutput
from inventory.services.list_products import list_products as list_products_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListOutput)
async def list_products(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await list_products_service(limit, offset)
