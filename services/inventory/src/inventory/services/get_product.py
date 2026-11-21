from uuid import UUID

from inventory.exceptions import ProductNotFound
from inventory.models import Product
from inventory.schemas.product import ProductOutput


async def get_product(product_id: UUID) -> ProductOutput:
    product = await Product.get_or_none(id=product_id)
    if product is None:
        raise ProductNotFound()
    return ProductOutput.model_validate(product)
