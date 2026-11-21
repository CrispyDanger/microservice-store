from uuid import UUID

from fastapi import APIRouter, Depends

from inventory.dependencies import require_admin
from inventory.schemas.product import ProductOutput, RestockInput
from inventory.services.restock_product import restock_product as restock_product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "/{product_id}/restock", response_model=ProductOutput, dependencies=[Depends(require_admin)]
)
async def restock_product(product_id: UUID, body: RestockInput):
    return await restock_product_service(product_id, body.quantity)
