from decimal import Decimal
from uuid import uuid4

import pytest

from events.inventory import ReservedItem, StockRejected, StockReserved
from events.payments import PaymentFailed, PaymentSucceeded
from order.consuming import handle_message
from order.models import Event, Order, OrderItem, OrderStatus, ProcessedEvent


@pytest.fixture
async def order() -> Order:
    return await Order.create(user_id=uuid4(), total=Decimal("29.97"))


def as_kafka_value(event) -> bytes:
    return event.model_dump_json().encode()


@pytest.mark.parametrize(
    ("make_event", "expected_status"),
    [
        (
            lambda o: PaymentSucceeded(order_id=o.id, payment_id=uuid4(), amount=o.total),
            OrderStatus.CONFIRMED,
        ),
        (lambda o: PaymentFailed(order_id=o.id, reason="declined"), OrderStatus.CANCELLED),
        (lambda o: StockRejected(order_id=o.id, reason="sold out"), OrderStatus.CANCELLED),
    ],
)
async def test_a_message_reaches_its_handler(order, make_event, expected_status):
    await handle_message(as_kafka_value(make_event(order)))

    await order.refresh_from_db()
    assert order.status == expected_status
    assert await Event.all().count() == 1


async def test_stock_reserved_saves_the_total():
    order = await Order.create(user_id=uuid4())
    item = await OrderItem.create(order=order, product_id=uuid4(), quantity=2)
    event = StockReserved(
        order_id=order.id,
        items=[ReservedItem(product_id=item.product_id, quantity=2, unit_price=Decimal("9.99"))],
        total=Decimal("19.98"),
    )

    await handle_message(as_kafka_value(event))

    await order.refresh_from_db()
    assert order.total == Decimal("19.98")
    assert order.status == OrderStatus.PENDING


@pytest.mark.parametrize(
    "value",
    [
        b'{"type": "SomethingNew", "order_id": "x"}',
        b'{"order_id": "x"}',
    ],
)
async def test_messages_of_unknown_types_are_ignored(order, value):
    await handle_message(value)

    assert await ProcessedEvent.all().count() == 0


@pytest.mark.parametrize(
    "value",
    [
        b"not json",
        b"[1, 2, 3]",
        b'{"type": "PaymentFailed", "order_id": "x"}',
        b'{"type": "PaymentFailed", "order_id": "x", "reason": "declined"}',
        b"",
        None,
    ],
)
async def test_unreadable_messages_are_skipped(order, value):
    await handle_message(value)

    await order.refresh_from_db()
    assert order.status == OrderStatus.PENDING
    assert await ProcessedEvent.all().count() == 0
