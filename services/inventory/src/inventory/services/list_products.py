from inventory.models import Product
from inventory.schemas.product import ProductListOutput, ProductOutput


async def list_products(limit: int, offset: int) -> ProductListOutput:
    count = await Product.all().count()
    products = await Product.all().order_by("name", "id").offset(offset).limit(limit)
    return ProductListOutput(
        products=[ProductOutput.model_validate(product) for product in products],
        count=count,
        limit=limit,
        offset=offset,
    )
