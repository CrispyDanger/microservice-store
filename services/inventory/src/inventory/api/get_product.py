from uuid import UUID

from fastapi import APIRouter

from inventory.schemas.product import ProductOutput
from inventory.services.get_product import get_product as get_product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}", response_model=ProductOutput)
async def get_product(product_id: UUID):
    return await get_product_service(product_id)
