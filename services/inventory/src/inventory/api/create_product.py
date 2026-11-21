from fastapi import APIRouter, Depends

from inventory.dependencies import require_admin
from inventory.schemas.product import CreateProductInput, ProductOutput
from inventory.services.create_product import create_product as create_product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "", response_model=ProductOutput, status_code=201, dependencies=[Depends(require_admin)]
)
async def create_product(body: CreateProductInput):
    return await create_product_service(body)
