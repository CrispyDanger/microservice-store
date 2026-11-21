import json
from datetime import UTC, datetime
from uuid import uuid4

from events.inventory import INVENTORY_TOPIC, StockRejected
from inventory.models import Event
from inventory.publishing import publish_batch, record_event


async def _record(reason: str = "test") -> StockRejected:
    event = StockRejected(order_id=uuid4(), reason=reason)
    await record_event(INVENTORY_TOPIC, event)
    return event


async def test_publish_batch_sends_pending_events_in_order(producer):
    first = await _record("first")
    second = await _record("second")

    assert await publish_batch(producer) == 2

    assert [json.loads(value)["reason"] for _, _, value in producer.sent] == ["first", "second"]
    topic, key, _ = producer.sent[0]
    assert (topic, key) == (INVENTORY_TOPIC, str(first.order_id).encode())
    assert await Event.filter(published_at=None).count() == 0
    assert await Event.filter(id=second.event_id, published_at__not_isnull=True).exists()


async def test_publish_batch_skips_published_events(producer):
    event = await _record()
    await Event.filter(id=event.event_id).update(published_at=datetime.now(UTC))

    assert await publish_batch(producer) == 0
    assert producer.sent == []
