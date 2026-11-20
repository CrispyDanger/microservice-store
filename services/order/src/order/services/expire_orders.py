from datetime import UTC, datetime, timedelta

from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC, OrderCancelled
from order.models import Order, OrderStatus
from order.publishing import record_event

TIMEOUT_REASON = "timed out waiting for stock or payment"
BATCH_SIZE = 100


async def expire_pending_orders(older_than: timedelta) -> int:
    cutoff = datetime.now(UTC) - older_than
    async with in_transaction():
        orders = await (
            Order.filter(status=OrderStatus.PENDING, created_at__lt=cutoff)
            .order_by("created_at")
            .limit(BATCH_SIZE)
            .select_for_update(skip_locked=True)
        )
        for order in orders:
            order.status = OrderStatus.CANCELLED
            order.cancel_reason = TIMEOUT_REASON
            await order.save(update_fields=["status", "cancel_reason", "updated_at"])
            await record_event(
                ORDERS_TOPIC, OrderCancelled(order_id=order.id, reason=TIMEOUT_REASON)
            )
    return len(orders)
