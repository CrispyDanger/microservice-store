import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from tortoise.transactions import in_transaction

from events.orders import OrderCreated, OrderItem
from inventory.models import (
    Event,
    ProcessedEvent,
    Product,
    StockReservation,
    StockReservationItem,
    StockReservationStatus,
)
from inventory.services.reserve_stock import reserve_stock


async def make_product(price: str = "10.00", stock: int = 5) -> Product:
    return await Product.create(name="Mug", price=Decimal(price), stock=stock)


def order_created(*lines: tuple[Product, int]) -> OrderCreated:
    return OrderCreated(
        order_id=uuid4(),
        user_id=uuid4(),
        items=[OrderItem(product_id=product.id, quantity=quantity) for product, quantity in lines],
        total=Decimal("1.00"),
    )


async def stock_of(product: Product) -> int:
    await product.refresh_from_db()
    return product.stock


@pytest.fixture
async def mug() -> Product:
    return await make_product(price="9.99", stock=5)


@pytest.fixture
async def teapot() -> Product:
    return await make_product(price="25.00", stock=2)


async def test_reserves_every_item_and_computes_the_total(mug, teapot):
    event = order_created((mug, 3), (teapot, 1))

    await reserve_stock(event)

    assert await stock_of(mug) == 2
    assert await stock_of(teapot) == 1
    reservation = await StockReservation.get(order_id=event.order_id)
    assert reservation.status == StockReservationStatus.RESERVED
    assert reservation.total == Decimal("54.97")
    items = {i.product_id: i for i in await StockReservationItem.all()}
    assert (items[mug.id].quantity, items[mug.id].unit_price) == (3, Decimal("9.99"))
    assert (items[teapot.id].quantity, items[teapot.id].unit_price) == (1, Decimal("25.00"))


async def test_records_stock_reserved_with_prices_and_total(mug):
    event = order_created((mug, 2))

    await reserve_stock(event)

    outbox = await Event.get()
    assert outbox.topic == "inventory"
    assert outbox.key == str(event.order_id)
    assert outbox.payload["type"] == "StockReserved"
    assert outbox.payload["total"] == "19.98"
    assert outbox.payload["items"] == [
        {"product_id": str(mug.id), "quantity": 2, "unit_price": "9.99"}
    ]


async def test_the_client_total_is_ignored(mug):
    event = order_created((mug, 1))

    await reserve_stock(event)

    reservation = await StockReservation.get(order_id=event.order_id)
    assert reservation.total == Decimal("9.99")


async def test_taking_the_last_units_leaves_zero(teapot):
    await reserve_stock(order_created((teapot, 2)))

    assert await stock_of(teapot) == 0


async def test_rejects_when_stock_is_short_and_changes_nothing(mug):
    event = order_created((mug, 6))

    await reserve_stock(event)

    assert await stock_of(mug) == 5
    reservation = await StockReservation.get(order_id=event.order_id)
    assert reservation.status == StockReservationStatus.REJECTED
    assert reservation.total is None
    assert "requested 6, available 5" in reservation.reject_reason
    assert not await StockReservationItem.exists()
    outbox = await Event.get()
    assert outbox.payload["type"] == "StockRejected"
    assert outbox.payload["reason"] == reservation.reject_reason


async def test_one_short_item_rejects_the_whole_order(mug, teapot):
    await reserve_stock(order_created((mug, 1), (teapot, 3)))

    assert await stock_of(mug) == 5
    assert await stock_of(teapot) == 2
    reservation = await StockReservation.get()
    assert reservation.status == StockReservationStatus.REJECTED


async def test_rejects_an_unknown_product(mug):
    missing = Product(id=uuid4())
    event = order_created((mug, 1), (missing, 1))

    await reserve_stock(event)

    reservation = await StockReservation.get(order_id=event.order_id)
    assert reservation.reject_reason == f"unknown product {missing.id}"
    assert await stock_of(mug) == 5


async def test_a_duplicate_event_is_applied_once(mug):
    event = order_created((mug, 2))

    await reserve_stock(event)
    await reserve_stock(event)

    assert await stock_of(mug) == 3
    assert await Event.all().count() == 1
    assert await ProcessedEvent.all().count() == 1


async def test_later_price_changes_do_not_touch_the_reservation(mug):
    await reserve_stock(order_created((mug, 1)))

    await Product.filter(id=mug.id).update(price=Decimal("50.00"))

    item = await StockReservationItem.get()
    assert item.unit_price == Decimal("9.99")


async def test_two_orders_racing_for_the_last_unit():
    product = await make_product(stock=1)
    first, second = order_created((product, 1)), order_created((product, 1))

    await asyncio.gather(reserve_stock(first), reserve_stock(second))

    statuses = sorted(r.status for r in await StockReservation.all())
    assert statuses == [StockReservationStatus.REJECTED, StockReservationStatus.RESERVED]
    assert await stock_of(product) == 0


async def test_reservation_waits_for_a_concurrent_stock_change():
    product = await make_product(stock=1)
    locked, release = asyncio.Event(), asyncio.Event()

    async def other_order_holding_the_lock():
        async with in_transaction():
            await Product.select_for_update().get(id=product.id)
            locked.set()
            await release.wait()
            await Product.filter(id=product.id).update(stock=0)

    other = asyncio.create_task(other_order_holding_the_lock())
    await locked.wait()
    reservation = asyncio.create_task(reserve_stock(order_created((product, 1))))
    await asyncio.sleep(0.3)
    assert not reservation.done()

    release.set()
    await other
    await reservation

    assert (await StockReservation.get()).status == StockReservationStatus.REJECTED
    assert await stock_of(product) == 0
