from uuid import UUID

from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC, OrderCancelled
from order.exceptions import OrderNotCancellable, OrderNotFound
from order.models import Order, OrderStatus
from order.publishing import record_event
from order.schemas.order import OrderOutput

DEFAULT_CANCEL_REASON = "cancelled by user"


async def cancel_order(order_id: UUID, user_id: UUID, reason: str | None) -> OrderOutput:
    async with in_transaction():
        order = await Order.select_for_update().get_or_none(id=order_id, user_id=user_id)
        if order is None:
            raise OrderNotFound()
        if order.status != OrderStatus.PENDING:
            raise OrderNotCancellable()
        order.status = OrderStatus.CANCELLED
        order.cancel_reason = reason or DEFAULT_CANCEL_REASON
        await order.save(update_fields=["status", "cancel_reason", "updated_at"])
        event = OrderCancelled(order_id=order.id, reason=order.cancel_reason)
        await record_event(ORDERS_TOPIC, event)

    await order.fetch_related("items")
    return OrderOutput.model_validate(order)
