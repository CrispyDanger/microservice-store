from decimal import Decimal
from uuid import uuid4

import pytest

from events.orders import OrderCancelled, OrderConfirmed, OrderCreated, OrderItem
from inventory.consuming import handle_message
from inventory.models import ProcessedEvent, Product, StockReservation, StockReservationStatus


@pytest.fixture
async def product() -> Product:
    return await Product.create(name="Mug", price=Decimal("9.99"), stock=5)


def order_created(product: Product, quantity: int = 2) -> OrderCreated:
    return OrderCreated(
        order_id=uuid4(),
        user_id=uuid4(),
        items=[OrderItem(product_id=product.id, quantity=quantity)],
    )


def as_kafka_value(event) -> bytes:
    return event.model_dump_json().encode()


async def test_order_created_reserves_stock(product):
    await handle_message(as_kafka_value(order_created(product)))

    await product.refresh_from_db()
    assert product.stock == 3
    assert (await StockReservation.get()).status == StockReservationStatus.RESERVED


async def test_order_cancelled_releases_stock(product):
    created = order_created(product)
    await handle_message(as_kafka_value(created))

    await handle_message(as_kafka_value(OrderCancelled(order_id=created.order_id, reason="x")))

    await product.refresh_from_db()
    assert product.stock == 5
    assert (await StockReservation.get()).status == StockReservationStatus.RELEASED


async def test_order_confirmed_is_ignored():
    await handle_message(as_kafka_value(OrderConfirmed(order_id=uuid4())))

    assert await ProcessedEvent.all().count() == 0


@pytest.mark.parametrize(
    "value",
    [
        b"",
        b"{}",
        b"not json",
        b"[1, 2]",
        b'{"type": "OrderCreated"}',
        b'{"type": "OrderCancelled", "order_id": "not-a-uuid", "reason": "x"}',
    ],
)
async def test_unreadable_messages_are_skipped(value):
    await handle_message(value)

    assert await ProcessedEvent.all().count() == 0
