from uuid import UUID

from order.models import Order
from order.schemas.order import OrderListOutput, OrderOutput


async def list_orders(user_id: UUID, limit: int, offset: int) -> OrderListOutput:
    query = Order.filter(user_id=user_id)
    count = await query.count()
    orders = (
        await query.order_by("-created_at", "-id")
        .offset(offset)
        .limit(limit)
        .prefetch_related("items")
    )
    return OrderListOutput(
        orders=[OrderOutput.model_validate(order) for order in orders],
        count=count,
        limit=limit,
        offset=offset,
    )
