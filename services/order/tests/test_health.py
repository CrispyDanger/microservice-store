from datetime import UTC, datetime, timedelta
from uuid import uuid4

from events.orders import ORDERS_TOPIC, OrderCancelled
from order.models import Event
from order.publishing import record_event


async def make_event(created_at: datetime, published_at: datetime | None = None) -> None:
    event = OrderCancelled(order_id=uuid4(), reason="test")
    await record_event(ORDERS_TOPIC, event)
    await Event.filter(id=event.event_id).update(created_at=created_at, published_at=published_at)


def ago(**kwargs) -> datetime:
    return datetime.now(UTC) - timedelta(**kwargs)


async def test_health(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_relay_health_with_no_events(client):
    resp = await client.get("/health/relay")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "oldest_unpublished_seconds": 0}


async def test_relay_health_ignores_published_events(client):
    await make_event(created_at=ago(hours=1), published_at=ago(hours=1))

    resp = await client.get("/health/relay")

    assert resp.json()["oldest_unpublished_seconds"] == 0


async def test_relay_health_reports_the_oldest_unpublished_event(client):
    await make_event(created_at=ago(seconds=30))
    await make_event(created_at=ago(seconds=10))

    resp = await client.get("/health/relay")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert 30 <= resp.json()["oldest_unpublished_seconds"] < 35


async def test_relay_health_is_unavailable_when_the_relay_is_stuck(client):
    await make_event(created_at=ago(minutes=5))

    resp = await client.get("/health/relay")

    assert resp.status_code == 503
    assert resp.json()["status"] == "stalled"
    assert resp.json()["oldest_unpublished_seconds"] >= 300


async def test_health_stays_ok_when_the_relay_is_stuck(client):
    await make_event(created_at=ago(minutes=5))

    resp = await client.get("/health")

    assert resp.status_code == 200
