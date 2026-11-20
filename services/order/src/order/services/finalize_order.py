import logging

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from events.base import Event as BaseEvent
from events.inventory import StockRejected
from events.orders import ORDERS_TOPIC, OrderCancelled, OrderConfirmed
from events.payments import PaymentFailed, PaymentSucceeded
from order.models import Order, OrderStatus, ProcessedEvent
from order.publishing import record_event

logger = logging.getLogger(__name__)


async def _lock_pending_order(event: BaseEvent) -> Order | None:
    await ProcessedEvent.create(event_id=event.event_id)
    order = await Order.select_for_update().get_or_none(id=event.order_id)
    name = type(event).__name__
    if order is None:
        logger.warning("%s for unknown order %s", name, event.order_id)
        return None
    if order.status != OrderStatus.PENDING:
        logger.info("%s ignored, order %s is %s", name, order.id, order.status)
        return None
    return order


async def _confirm(event: BaseEvent) -> None:
    try:
        async with in_transaction():
            order = await _lock_pending_order(event)
            if order is None:
                return
            order.status = OrderStatus.CONFIRMED
            await order.save(update_fields=["status", "updated_at"])
            await record_event(ORDERS_TOPIC, OrderConfirmed(order_id=order.id))
    except IntegrityError:
        logger.info("Duplicate event %s skipped", event.event_id)


async def _cancel(event: BaseEvent, reason: str) -> None:
    try:
        async with in_transaction():
            order = await _lock_pending_order(event)
            if order is None:
                return
            order.status = OrderStatus.CANCELLED
            order.cancel_reason = reason[:255]
            await order.save(update_fields=["status", "cancel_reason", "updated_at"])
            await record_event(
                ORDERS_TOPIC, OrderCancelled(order_id=order.id, reason=order.cancel_reason)
            )
    except IntegrityError:
        logger.info("Duplicate event %s skipped", event.event_id)


async def handle_payment_succeeded(event: PaymentSucceeded) -> None:
    await _confirm(event)


async def handle_payment_failed(event: PaymentFailed) -> None:
    await _cancel(event, f"payment failed: {event.reason}")


async def handle_stock_rejected(event: StockRejected) -> None:
    await _cancel(event, f"out of stock: {event.reason}")
