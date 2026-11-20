import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from tortoise.transactions import in_transaction

from events.inventory import StockRejected
from events.orders import ORDERS_TOPIC
from events.payments import PaymentFailed, PaymentSucceeded
from order.models import Event, Order, OrderStatus, ProcessedEvent
from order.services.finalize_order import (
    handle_payment_failed,
    handle_payment_succeeded,
    handle_stock_rejected,
)


@pytest.fixture
async def order() -> Order:
    return await Order.create(user_id=uuid4(), total=Decimal("29.97"))


def paid(order: Order) -> PaymentSucceeded:
    return PaymentSucceeded(order_id=order.id, payment_id=uuid4(), amount=order.total)


async def test_payment_succeeded_confirms_the_order(order):
    await handle_payment_succeeded(paid(order))

    await order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED
    [row] = await Event.all()
    assert row.topic == ORDERS_TOPIC
    assert row.key == str(order.id)
    assert row.payload["type"] == "OrderConfirmed"


@pytest.mark.parametrize(
    ("handle", "event_cls", "expected_reason"),
    [
        (handle_payment_failed, PaymentFailed, "payment failed: card declined"),
        (handle_stock_rejected, StockRejected, "out of stock: card declined"),
    ],
)
async def test_failures_cancel_the_order_with_a_reason(order, handle, event_cls, expected_reason):
    await handle(event_cls(order_id=order.id, reason="card declined"))

    await order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED
    assert order.cancel_reason == expected_reason
    [row] = await Event.all()
    assert row.payload["type"] == "OrderCancelled"
    assert row.payload["reason"] == expected_reason


async def test_a_long_reason_is_cut_to_fit_the_column(order):
    await handle_payment_failed(PaymentFailed(order_id=order.id, reason="x" * 500))

    await order.refresh_from_db()
    assert len(order.cancel_reason) == 255


async def test_a_redelivered_event_is_handled_once(order):
    event = paid(order)

    await handle_payment_succeeded(event)
    await handle_payment_succeeded(event)

    assert await ProcessedEvent.filter(event_id=event.event_id).count() == 1
    assert await Event.all().count() == 1


async def test_an_event_for_a_cancelled_order_changes_nothing(order):
    await Order.filter(id=order.id).update(status=OrderStatus.CANCELLED)

    await handle_payment_succeeded(paid(order))

    await order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED
    assert await Event.all().count() == 0
    assert await ProcessedEvent.all().count() == 1


async def test_an_event_for_an_unknown_order_is_marked_processed():
    event = PaymentFailed(order_id=uuid4(), reason="card declined")

    await handle_payment_failed(event)

    assert await ProcessedEvent.filter(event_id=event.event_id).exists()
    assert await Event.all().count() == 0


async def test_payment_waits_for_a_concurrent_user_cancel_and_then_loses(order):
    locked, release = asyncio.Event(), asyncio.Event()

    async def user_cancel_holding_the_lock():
        async with in_transaction():
            await Order.select_for_update().get(id=order.id)
            locked.set()
            await release.wait()
            await Order.filter(id=order.id).update(status=OrderStatus.CANCELLED)

    cancel = asyncio.create_task(user_cancel_holding_the_lock())
    await locked.wait()
    payment = asyncio.create_task(handle_payment_succeeded(paid(order)))
    await asyncio.sleep(0.3)
    assert not payment.done()

    release.set()
    await cancel
    await payment

    await order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED
    assert await Event.all().count() == 0
