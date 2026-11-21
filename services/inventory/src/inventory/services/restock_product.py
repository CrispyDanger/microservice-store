from uuid import UUID

from tortoise.expressions import F

from inventory.exceptions import ProductNotFound
from inventory.models import Product
from inventory.schemas.product import ProductOutput


async def restock_product(product_id: UUID, quantity: int) -> ProductOutput:
    updated = await Product.filter(id=product_id).update(stock=F("stock") + quantity)
    if not updated:
        raise ProductNotFound()
    return ProductOutput.model_validate(await Product.get(id=product_id))
