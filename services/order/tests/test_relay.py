import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC, OrderCancelled
from order.models import Event
from order.publishing import publish_batch, record_event

from tests.conftest import with_new_key


class BrokenProducer:
    async def send_and_wait(self, topic: str, key: bytes, value: bytes) -> None:
        raise ConnectionError("kafka is down")


async def _record(reason: str = "test") -> OrderCancelled:
    event = OrderCancelled(order_id=uuid4(), reason=reason)
    await record_event(ORDERS_TOPIC, event)
    return event


async def test_publish_batch_with_nothing_pending_sends_nothing(producer):
    assert await publish_batch(producer) == 0
    assert producer.sent == []


async def test_publish_batch_sends_a_placed_order_as_order_created(
    client, producer, auth_headers, order_payload
):
    resp = await client.post("/orders", json=order_payload, headers=with_new_key(auth_headers))
    order_id = resp.json()["id"]

    assert await publish_batch(producer) == 1

    [(topic, key, value)] = producer.sent
    assert topic == ORDERS_TOPIC
    assert key == order_id.encode()
    event = json.loads(value)
    assert event["type"] == "OrderCreated"
    assert event["order_id"] == order_id
    assert event["items"] == order_payload["items"]
    assert event["total"] == "29.97"


async def test_publish_batch_sends_oldest_first_and_marks_events_published(producer):
    recorded = [await _record(f"reason {n}") for n in range(3)]

    await publish_batch(producer)

    sent_ids = [json.loads(value)["event_id"] for _, _, value in producer.sent]
    assert sent_ids == [str(e.event_id) for e in recorded]
    assert await Event.filter(published_at=None).count() == 0


async def test_publish_batch_skips_events_already_published(producer):
    await _record()
    await publish_batch(producer)
    producer.sent.clear()

    assert await publish_batch(producer) == 0
    assert producer.sent == []


async def test_a_failed_send_leaves_events_unpublished(producer):
    await _record()

    with pytest.raises(ConnectionError):
        await publish_batch(BrokenProducer())

    assert await Event.filter(published_at=None).count() == 1
    assert await publish_batch(producer) == 1


async def test_publish_batch_skips_events_locked_by_another_relay(producer):
    locked_event = await _record("locked")
    free_event = await _record("free")
    locked, release = asyncio.Event(), asyncio.Event()

    async def other_relay_holding_a_row():
        async with in_transaction():
            await Event.filter(id=locked_event.event_id).select_for_update()
            locked.set()
            await release.wait()
            await Event.filter(id=locked_event.event_id).update(published_at=datetime.now(UTC))

    other = asyncio.create_task(other_relay_holding_a_row())
    await locked.wait()

    sent = await asyncio.wait_for(publish_batch(producer), timeout=2)

    release.set()
    await other
    assert sent == 1
    assert json.loads(producer.sent[0][2])["event_id"] == str(free_event.event_id)
    assert await Event.filter(published_at=None).count() == 0
