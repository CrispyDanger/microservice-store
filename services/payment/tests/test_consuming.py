from decimal import Decimal
from uuid import uuid4

import pytest

from events.inventory import ReservedItem, StockRejected, StockReserved
from payment.consuming import handle_message
from payment.models import Payment, PaymentStatus, ProcessedEvent


def as_kafka_value(event) -> bytes:
    return event.model_dump_json().encode()


async def test_stock_reserved_charges_the_order():
    event = StockReserved(
        order_id=uuid4(),
        items=[ReservedItem(product_id=uuid4(), quantity=1, unit_price=Decimal("9.99"))],
        total=Decimal("9.99"),
    )

    await handle_message(as_kafka_value(event))

    assert (await Payment.get(order_id=event.order_id)).status == PaymentStatus.SUCCEEDED


async def test_stock_rejected_is_ignored():
    await handle_message(as_kafka_value(StockRejected(order_id=uuid4(), reason="x")))

    assert await ProcessedEvent.all().count() == 0
    assert not await Payment.exists()


@pytest.mark.parametrize(
    "value",
    [
        b"",
        b"{}",
        b"not json",
        b"[1, 2]",
        b'{"type": "StockReserved"}',
        b'{"type": "StockReserved", "order_id": "not-a-uuid", "items": [], "total": "1"}',
    ],
)
async def test_unreadable_messages_are_skipped(value):
    await handle_message(value)

    assert await ProcessedEvent.all().count() == 0
