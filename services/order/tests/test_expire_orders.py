import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC
from order.models import Event, Order, OrderStatus
from order.services.expire_orders import TIMEOUT_REASON, expire_pending_orders

TIMEOUT = timedelta(minutes=15)


async def make_order(age: timedelta, status: OrderStatus = OrderStatus.PENDING) -> Order:
    order = await Order.create(user_id=uuid4(), total=Decimal("29.97"))
    await Order.filter(id=order.id).update(created_at=datetime.now(UTC) - age, status=status)
    return order


async def test_an_old_pending_order_is_cancelled_and_announced():
    order = await make_order(age=timedelta(minutes=20))

    assert await expire_pending_orders(TIMEOUT) == 1

    await order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED
    assert order.cancel_reason == TIMEOUT_REASON
    [row] = await Event.all()
    assert row.topic == ORDERS_TOPIC
    assert row.key == str(order.id)
    assert row.payload["type"] == "OrderCancelled"
    assert row.payload["reason"] == TIMEOUT_REASON


async def test_a_fresh_pending_order_is_left_alone():
    order = await make_order(age=timedelta(minutes=5))

    assert await expire_pending_orders(TIMEOUT) == 0

    await order.refresh_from_db()
    assert order.status == OrderStatus.PENDING
    assert await Event.all().count() == 0


@pytest.mark.parametrize("status", [OrderStatus.CONFIRMED, OrderStatus.CANCELLED])
async def test_finished_orders_are_not_touched(status):
    order = await make_order(age=timedelta(hours=1), status=status)

    assert await expire_pending_orders(TIMEOUT) == 0

    await order.refresh_from_db()
    assert order.status == status
    assert await Event.all().count() == 0


async def test_a_second_run_finds_nothing_left():
    await make_order(age=timedelta(minutes=20))
    await expire_pending_orders(TIMEOUT)

    assert await expire_pending_orders(TIMEOUT) == 0
    assert await Event.all().count() == 1


async def test_an_order_locked_by_a_handler_is_skipped_until_the_next_run():
    busy = await make_order(age=timedelta(minutes=20))
    idle = await make_order(age=timedelta(minutes=20))
    locked, release = asyncio.Event(), asyncio.Event()

    async def handler_holding_the_lock():
        async with in_transaction():
            await Order.select_for_update().get(id=busy.id)
            locked.set()
            await release.wait()

    handler = asyncio.create_task(handler_holding_the_lock())
    await locked.wait()

    expired = await asyncio.wait_for(expire_pending_orders(TIMEOUT), timeout=2)

    release.set()
    await handler
    assert expired == 1
    await idle.refresh_from_db()
    await busy.refresh_from_db()
    assert idle.status == OrderStatus.CANCELLED
    assert busy.status == OrderStatus.PENDING

    assert await expire_pending_orders(TIMEOUT) == 1
    await busy.refresh_from_db()
    assert busy.status == OrderStatus.CANCELLED
