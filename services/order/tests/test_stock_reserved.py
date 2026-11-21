from decimal import Decimal
from uuid import uuid4

import pytest

from events.inventory import ReservedItem, StockReserved
from order.models import Event, Order, OrderItem, OrderStatus, ProcessedEvent
from order.services.finalize_order import handle_stock_reserved


@pytest.fixture
async def order() -> Order:
    order = await Order.create(user_id=uuid4())
    await OrderItem.create(order=order, product_id=uuid4(), quantity=2)
    await OrderItem.create(order=order, product_id=uuid4(), quantity=1)
    return order


async def reserved(order: Order, total: str = "44.98") -> StockReserved:
    items = await OrderItem.filter(order=order).order_by("quantity")
    prices = {1: Decimal("25.00"), 2: Decimal("9.99")}
    return StockReserved(
        order_id=order.id,
        items=[
            ReservedItem(
                product_id=i.product_id, quantity=i.quantity, unit_price=prices[i.quantity]
            )
            for i in items
        ],
        total=Decimal(total),
    )


async def unit_prices(order: Order) -> dict[int, Decimal | None]:
    return {i.quantity: i.unit_price for i in await OrderItem.filter(order=order)}


async def test_saves_the_total_and_unit_prices(order):
    await handle_stock_reserved(await reserved(order))

    await order.refresh_from_db()
    assert order.total == Decimal("44.98")
    assert await unit_prices(order) == {1: Decimal("25.00"), 2: Decimal("9.99")}


async def test_order_stays_pending_and_no_event_is_recorded(order):
    await handle_stock_reserved(await reserved(order))

    await order.refresh_from_db()
    assert order.status == OrderStatus.PENDING
    assert await Event.all().count() == 0


@pytest.mark.parametrize("status", [OrderStatus.CONFIRMED, OrderStatus.CANCELLED])
async def test_a_late_event_still_saves_the_prices(order, status):
    await Order.filter(id=order.id).update(status=status)

    await handle_stock_reserved(await reserved(order))

    await order.refresh_from_db()
    assert order.status == status
    assert order.total == Decimal("44.98")
    assert await unit_prices(order) == {1: Decimal("25.00"), 2: Decimal("9.99")}


async def test_an_order_that_already_has_a_total_is_left_alone(order):
    await Order.filter(id=order.id).update(total=Decimal("10.00"))

    await handle_stock_reserved(await reserved(order))

    await order.refresh_from_db()
    assert order.total == Decimal("10.00")
    assert await unit_prices(order) == {1: None, 2: None}


async def test_a_duplicate_event_is_skipped(order):
    event = await reserved(order)

    await handle_stock_reserved(event)
    await handle_stock_reserved(event)

    assert await ProcessedEvent.all().count() == 1


async def test_an_unknown_order_is_ignored():
    await handle_stock_reserved(StockReserved(order_id=uuid4(), items=[], total=Decimal("1.00")))

    assert await ProcessedEvent.all().count() == 1
