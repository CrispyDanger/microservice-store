import asyncio
import json
import logging
from datetime import UTC, datetime

from aiokafka import AIOKafkaProducer
from tortoise.transactions import in_transaction

from events.base import Event as BaseEvent
from order.config import settings
from order.models import Event

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
IDLE_DELAY = 1.0
MIN_BACKOFF = 1.0
MAX_BACKOFF = 30.0


async def record_event(topic: str, event: BaseEvent) -> None:
    await Event.create(
        id=event.event_id,
        topic=topic,
        key=str(event.order_id),
        payload=event.model_dump(mode="json"),
    )


async def publish_batch(producer: AIOKafkaProducer) -> int:
    async with in_transaction():
        events = await (
            Event.filter(published_at=None)
            .order_by("created_at")
            .limit(BATCH_SIZE)
            .select_for_update(skip_locked=True)
        )
        for event in events:
            value = json.dumps(event.payload, separators=(",", ":")).encode()
            await producer.send_and_wait(event.topic, key=event.key.encode(), value=value)
        if events:
            await Event.filter(id__in=[e.id for e in events]).update(
                published_at=datetime.now(UTC)
            )
    return len(events)


async def run_relay() -> None:
    delay = MIN_BACKOFF
    while True:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers, enable_idempotence=True
        )
        try:
            await producer.start()
            while True:
                sent = await publish_batch(producer)
                delay = MIN_BACKOFF
                if sent == 0:
                    await asyncio.sleep(IDLE_DELAY)
        except Exception:
            logger.exception("Event relay failed, retrying in %.0fs", delay)
        finally:
            await producer.stop()
        await asyncio.sleep(delay)
        delay = min(delay * 2, MAX_BACKOFF)
