from inventory.models import Product
from inventory.schemas.product import CreateProductInput, ProductOutput


async def create_product(data: CreateProductInput) -> ProductOutput:
    product = await Product.create(name=data.name, price=data.price, stock=data.stock)
    return ProductOutput.model_validate(product)
