from datetime import UTC, datetime, timedelta
from uuid import uuid4

from events.inventory import INVENTORY_TOPIC, StockRejected
from inventory.models import Event
from inventory.publishing import record_event


async def make_event(created_at: datetime) -> None:
    event = StockRejected(order_id=uuid4(), reason="test")
    await record_event(INVENTORY_TOPIC, event)
    await Event.filter(id=event.event_id).update(created_at=created_at)


async def test_health(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_relay_health_with_no_events(client):
    resp = await client.get("/health/relay")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "oldest_unpublished_seconds": 0}


async def test_relay_health_is_unavailable_when_the_relay_is_stuck(client):
    await make_event(created_at=datetime.now(UTC) - timedelta(minutes=5))

    resp = await client.get("/health/relay")

    assert resp.status_code == 503
    assert resp.json()["status"] == "stalled"
