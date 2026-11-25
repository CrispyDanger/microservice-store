from decimal import Decimal
from uuid import uuid4

from events.inventory import ReservedItem, StockReserved
from events.payments import PAYMENTS_TOPIC
from payment.gateway import gateway
from payment.models import Event, Payment, PaymentStatus, ProcessedEvent
from payment.services.charge_payment import charge_payment


def stock_reserved(total: str = "19.98") -> StockReserved:
    return StockReserved(
        order_id=uuid4(),
        items=[ReservedItem(product_id=uuid4(), quantity=2, unit_price=Decimal(total) / 2)],
        total=Decimal(total),
    )


async def test_charges_the_total_and_records_payment_succeeded():
    event = stock_reserved("19.98")

    await charge_payment(event)

    payment = await Payment.get(order_id=event.order_id)
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.amount == Decimal("19.98")
    assert gateway.charges == {event.order_id: Decimal("19.98")}

    recorded = await Event.get()
    assert recorded.topic == PAYMENTS_TOPIC
    assert recorded.key == str(event.order_id)
    assert recorded.payload["type"] == "PaymentSucceeded"
    assert recorded.payload["payment_id"] == str(payment.id)
    assert recorded.payload["amount"] == "19.98"


async def test_a_declined_charge_records_payment_failed():
    event = stock_reserved("5000.00")

    await charge_payment(event)

    payment = await Payment.get(order_id=event.order_id)
    assert payment.status == PaymentStatus.FAILED
    assert "over the limit" in payment.failure_reason
    assert gateway.charges == {}

    recorded = await Event.get()
    assert recorded.payload["type"] == "PaymentFailed"
    assert recorded.payload["reason"] == payment.failure_reason


async def test_the_limit_itself_is_accepted():
    event = stock_reserved(str(gateway.decline_over))

    await charge_payment(event)

    assert (await Payment.get()).status == PaymentStatus.SUCCEEDED


async def test_a_duplicate_event_charges_once():
    event = stock_reserved()

    await charge_payment(event)
    await charge_payment(event)

    assert await Payment.all().count() == 1
    assert await Event.all().count() == 1
    assert await ProcessedEvent.all().count() == 1


async def test_a_second_stock_reserved_for_the_same_order_charges_once():
    first = stock_reserved()
    second = StockReserved(order_id=first.order_id, items=first.items, total=first.total)

    await charge_payment(first)
    await charge_payment(second)

    assert await Payment.all().count() == 1
    assert await Event.all().count() == 1
    assert await ProcessedEvent.all().count() == 2
