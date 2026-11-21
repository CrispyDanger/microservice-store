from decimal import Decimal
from uuid import UUID, uuid4

from events.orders import OrderCancelled, OrderCreated, OrderItem
from inventory.models import (
    Event,
    ProcessedEvent,
    Product,
    StockReservation,
    StockReservationStatus,
)
from inventory.services.release_stock import release_stock
from inventory.services.reserve_stock import reserve_stock


async def make_product(name: str = "Mug", stock: int = 5) -> Product:
    return await Product.create(name=name, price=Decimal("9.99"), stock=stock)


async def reserve(*lines: tuple[Product, int]) -> UUID:
    event = OrderCreated(
        order_id=uuid4(),
        user_id=uuid4(),
        items=[OrderItem(product_id=product.id, quantity=quantity) for product, quantity in lines],
    )
    await reserve_stock(event)
    return event.order_id


def cancelled(order_id: UUID) -> OrderCancelled:
    return OrderCancelled(order_id=order_id, reason="test")


async def stock_of(product: Product) -> int:
    await product.refresh_from_db()
    return product.stock


async def test_cancel_returns_the_reserved_stock():
    product = await make_product(stock=5)
    order_id = await reserve((product, 3))

    await release_stock(cancelled(order_id))

    assert await stock_of(product) == 5
    reservation = await StockReservation.get(order_id=order_id)
    assert reservation.status == StockReservationStatus.RELEASED


async def test_release_returns_every_item():
    mug = await make_product("Mug", stock=5)
    teapot = await make_product("Teapot", stock=2)
    order_id = await reserve((mug, 2), (teapot, 2))

    await release_stock(cancelled(order_id))

    assert await stock_of(mug) == 5
    assert await stock_of(teapot) == 2


async def test_two_cancel_events_release_the_stock_once():
    product = await make_product(stock=5)
    order_id = await reserve((product, 3))

    await release_stock(cancelled(order_id))
    await release_stock(cancelled(order_id))

    assert await stock_of(product) == 5


async def test_a_duplicate_cancel_event_is_skipped():
    product = await make_product(stock=5)
    order_id = await reserve((product, 3))
    event = cancelled(order_id)

    await release_stock(event)
    await release_stock(event)

    assert await stock_of(product) == 5
    assert await ProcessedEvent.all().count() == 2


async def test_a_rejected_order_has_nothing_to_release():
    product = await make_product(stock=1)
    order_id = await reserve((product, 5))

    await release_stock(cancelled(order_id))

    assert await stock_of(product) == 1
    reservation = await StockReservation.get(order_id=order_id)
    assert reservation.status == StockReservationStatus.REJECTED


async def test_cancel_for_an_unknown_order_does_nothing():
    await release_stock(cancelled(uuid4()))

    assert await ProcessedEvent.all().count() == 1
    assert not await StockReservation.exists()


async def test_release_records_no_event():
    product = await make_product(stock=5)
    order_id = await reserve((product, 1))

    await release_stock(cancelled(order_id))

    assert await Event.all().count() == 1
