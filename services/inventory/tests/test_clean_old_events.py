from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from events.inventory import INVENTORY_TOPIC, StockRejected
from inventory.models import Event, ProcessedEvent, StockReservation, StockReservationStatus
from inventory.publishing import record_event
from inventory.services.clean_old_events import clean_old_events


def ago(**kwargs) -> datetime:
    return datetime.now(UTC) - timedelta(**kwargs)


async def make_event(published_at: datetime | None) -> Event:
    event = StockRejected(order_id=uuid4(), reason="test")
    await record_event(INVENTORY_TOPIC, event)
    await Event.filter(id=event.event_id).update(published_at=published_at)
    return await Event.get(id=event.event_id)


async def make_processed_event(processed_at: datetime) -> ProcessedEvent:
    row = await ProcessedEvent.create(event_id=uuid4())
    await ProcessedEvent.filter(event_id=row.event_id).update(processed_at=processed_at)
    return row


async def test_published_events_are_kept_for_seven_days():
    old = await make_event(published_at=ago(days=8))
    recent = await make_event(published_at=ago(days=6))

    assert await clean_old_events() == 1

    assert not await Event.filter(id=old.id).exists()
    assert await Event.filter(id=recent.id).exists()


async def test_unpublished_events_are_never_deleted():
    await make_event(published_at=None)
    await Event.all().update(created_at=ago(days=30))

    assert await clean_old_events() == 0


async def test_processed_events_are_kept_for_fourteen_days():
    old = await make_processed_event(ago(days=15))
    recent = await make_processed_event(ago(days=10))

    assert await clean_old_events() == 1

    assert not await ProcessedEvent.filter(event_id=old.event_id).exists()
    assert await ProcessedEvent.filter(event_id=recent.event_id).exists()


async def test_stock_reservations_are_kept():
    await StockReservation.create(
        order_id=uuid4(), status=StockReservationStatus.RESERVED, total=Decimal("9.99")
    )
    await StockReservation.all().update(created_at=ago(days=365))

    assert await clean_old_events() == 0
    assert await StockReservation.all().count() == 1
