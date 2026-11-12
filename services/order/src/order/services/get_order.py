from uuid import UUID

from order.exceptions import OrderNotFound
from order.models import Order
from order.schemas.order import OrderOutput


async def get_order(order_id: UUID, user_id: UUID) -> OrderOutput:
    order = await Order.get_or_none(id=order_id, user_id=user_id).prefetch_related("items")
    if order is None:
        raise OrderNotFound()
    return OrderOutput.model_validate(order)
