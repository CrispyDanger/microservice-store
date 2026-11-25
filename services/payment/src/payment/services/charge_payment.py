import logging

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from events.inventory import StockReserved
from events.payments import PAYMENTS_TOPIC, PaymentFailed, PaymentSucceeded
from payment.gateway import PaymentDeclined, gateway
from payment.models import Payment, PaymentStatus, ProcessedEvent
from payment.publishing import record_event

logger = logging.getLogger(__name__)


async def charge_payment(event: StockReserved) -> None:
    try:
        async with in_transaction():
            await ProcessedEvent.create(event_id=event.event_id)
            if await Payment.exists(order_id=event.order_id):
                logger.info("Order %s is already charged", event.order_id)
                return
            try:
                await gateway.charge(event.order_id, event.total)
            except PaymentDeclined as exc:
                await Payment.create(
                    order_id=event.order_id,
                    amount=event.total,
                    status=PaymentStatus.FAILED,
                    failure_reason=exc.reason,
                )
                await record_event(
                    PAYMENTS_TOPIC, PaymentFailed(order_id=event.order_id, reason=exc.reason)
                )
                return
            payment = await Payment.create(
                order_id=event.order_id, amount=event.total, status=PaymentStatus.SUCCEEDED
            )
            await record_event(
                PAYMENTS_TOPIC,
                PaymentSucceeded(order_id=event.order_id, payment_id=payment.id, amount=event.total),
            )
    except IntegrityError:
        logger.info("Duplicate event %s skipped", event.event_id)
