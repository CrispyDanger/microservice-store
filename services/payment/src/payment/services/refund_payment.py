import logging

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from events.orders import OrderCancelled
from payment.gateway import gateway
from payment.locks import lock_order
from payment.models import CancelledOrder, Payment, PaymentStatus, ProcessedEvent

logger = logging.getLogger(__name__)


async def refund_payment(event: OrderCancelled) -> None:
    try:
        async with in_transaction() as conn:
            await ProcessedEvent.create(event_id=event.event_id)
            await lock_order(conn, event.order_id)
            if not await CancelledOrder.exists(order_id=event.order_id):
                await CancelledOrder.create(order_id=event.order_id)
            payment = await Payment.get_or_none(order_id=event.order_id)
            if payment is None or payment.status != PaymentStatus.SUCCEEDED:
                logger.info("Nothing to refund for order %s", event.order_id)
                return
            await gateway.refund(payment.id, payment.amount)
            payment.status = PaymentStatus.REFUNDED
            await payment.save(update_fields=["status", "updated_at"])
    except IntegrityError:
        logger.info("Duplicate event %s skipped", event.event_id)
