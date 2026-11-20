from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from events.orders import ORDERS_TOPIC, OrderCancelled
from order.models import Event, IdempotencyKey, Order, ProcessedEvent
from order.publishing import record_event
from order.services.purge_old_rows import purge_old_rows


def ago(**kwargs) -> datetime:
    return datetime.now(UTC) - timedelta(**kwargs)


async def make_event(published_at: datetime | None) -> Event:
    event = OrderCancelled(order_id=uuid4(), reason="test")
    await record_event(ORDERS_TOPIC, event)
    await Event.filter(id=event.event_id).update(published_at=published_at)
    return await Event.get(id=event.event_id)


async def make_processed_event(processed_at: datetime) -> ProcessedEvent:
    row = await ProcessedEvent.create(event_id=uuid4())
    await ProcessedEvent.filter(event_id=row.event_id).update(processed_at=processed_at)
    return row


async def make_idempotency_key(created_at: datetime) -> IdempotencyKey:
    order = await Order.create(user_id=uuid4(), total=Decimal("29.97"))
    key = await IdempotencyKey.create(
        user_id=order.user_id, key=uuid4(), request_hash="h", order=order
    )
    await IdempotencyKey.filter(id=key.id).update(created_at=created_at)
    return key


async def test_nothing_to_delete_returns_zero():
    assert await purge_old_rows() == 0


async def test_published_events_are_kept_for_seven_days():
    old = await make_event(published_at=ago(days=8))
    recent = await make_event(published_at=ago(days=6))

    await purge_old_rows()

    assert not await Event.filter(id=old.id).exists()
    assert await Event.filter(id=recent.id).exists()


async def test_unpublished_events_are_never_deleted():
    await make_event(published_at=None)
    await Event.all().update(created_at=ago(days=30))

    assert await purge_old_rows() == 0
    assert await Event.all().count() == 1


async def test_processed_events_are_kept_for_fourteen_days():
    old = await make_processed_event(ago(days=15))
    recent = await make_processed_event(ago(days=10))

    await purge_old_rows()

    assert not await ProcessedEvent.filter(event_id=old.event_id).exists()
    assert await ProcessedEvent.filter(event_id=recent.event_id).exists()


async def test_idempotency_keys_are_kept_for_a_day_and_their_orders_stay():
    old = await make_idempotency_key(ago(hours=25))
    recent = await make_idempotency_key(ago(hours=23))

    await purge_old_rows()

    assert not await IdempotencyKey.filter(id=old.id).exists()
    assert await IdempotencyKey.filter(id=recent.id).exists()
    assert await Order.all().count() == 2


async def test_returns_the_number_of_deleted_rows():
    await make_event(published_at=ago(days=8))
    await make_processed_event(ago(days=15))
    await make_idempotency_key(ago(hours=25))

    assert await purge_old_rows() == 3
