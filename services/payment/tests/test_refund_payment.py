import asyncio
from decimal import Decimal
from uuid import uuid4

from events.inventory import ReservedItem, StockReserved
from events.orders import OrderCancelled
from payment.gateway import gateway
from payment.models import CancelledOrder, Event, Payment, PaymentStatus, ProcessedEvent
from payment.services.charge_payment import charge_payment
from payment.services.refund_payment import refund_payment


def stock_reserved(total: str = "19.98") -> StockReserved:
    return StockReserved(
        order_id=uuid4(),
        items=[ReservedItem(product_id=uuid4(), quantity=1, unit_price=Decimal(total))],
        total=Decimal(total),
    )


def order_cancelled(order_id) -> OrderCancelled:
    return OrderCancelled(order_id=order_id, reason="cancelled by user")


async def test_a_succeeded_payment_is_refunded():
    reserved = stock_reserved("19.98")
    await charge_payment(reserved)

    await refund_payment(order_cancelled(reserved.order_id))

    payment = await Payment.get(order_id=reserved.order_id)
    assert payment.status == PaymentStatus.REFUNDED
    assert gateway.refunds == {payment.id: Decimal("19.98")}


async def test_a_failed_payment_is_not_refunded():
    reserved = stock_reserved("5000.00")
    await charge_payment(reserved)

    await refund_payment(order_cancelled(reserved.order_id))

    assert (await Payment.get(order_id=reserved.order_id)).status == PaymentStatus.FAILED
    assert gateway.refunds == {}


async def test_a_cancel_before_stock_reserved_prevents_the_charge():
    reserved = stock_reserved()

    await refund_payment(order_cancelled(reserved.order_id))
    await charge_payment(reserved)

    assert not await Payment.exists()
    assert gateway.charges == {}
    assert await Event.all().count() == 0
    assert await ProcessedEvent.all().count() == 2


async def test_a_duplicate_cancel_refunds_once():
    reserved = stock_reserved()
    await charge_payment(reserved)
    cancel = order_cancelled(reserved.order_id)

    await refund_payment(cancel)
    await refund_payment(cancel)

    assert len(gateway.refunds) == 1
    assert await CancelledOrder.all().count() == 1


async def test_a_second_cancel_for_the_same_order_refunds_once():
    reserved = stock_reserved()
    await charge_payment(reserved)

    await refund_payment(order_cancelled(reserved.order_id))
    await refund_payment(order_cancelled(reserved.order_id))

    assert (await Payment.get()).status == PaymentStatus.REFUNDED
    assert len(gateway.refunds) == 1
    assert await CancelledOrder.all().count() == 1


async def test_a_cancel_racing_a_charge_never_leaves_the_order_charged():
    for _ in range(20):
        reserved = stock_reserved()

        await asyncio.gather(
            charge_payment(reserved), refund_payment(order_cancelled(reserved.order_id))
        )

        payment = await Payment.get_or_none(order_id=reserved.order_id)
        assert payment is None or payment.status == PaymentStatus.REFUNDED
