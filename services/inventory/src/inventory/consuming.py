import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from events.orders import ORDERS_TOPIC, OrderCancelled, OrderCreated
from inventory.config import settings
from inventory.services.release_stock import release_stock
from inventory.services.reserve_stock import reserve_stock

logger = logging.getLogger(__name__)

GROUP_ID = "inventory"
MIN_BACKOFF = 1.0
MAX_BACKOFF = 30.0

ROUTES = {
    "OrderCreated": (OrderCreated, reserve_stock),
    "OrderCancelled": (OrderCancelled, release_stock),
}


async def handle_message(value: bytes) -> None:
    try:
        data = json.loads(value)
        event_type = data.get("type") if isinstance(data, dict) else None
        route = ROUTES.get(event_type)
        if route is None:
            return
        event_cls, handle = route
        event = event_cls.model_validate(data)
    except (ValueError, TypeError):
        logger.warning("Skipping unreadable message: %r", value[:200] if value else value)
        return
    await handle(event)


async def run_consumer() -> None:
    delay = MIN_BACKOFF
    while True:
        consumer = AIOKafkaConsumer(
            ORDERS_TOPIC,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=GROUP_ID,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
            async for message in consumer:
                await handle_message(message.value)
                await consumer.commit()
                delay = MIN_BACKOFF
        except Exception:
            logger.exception("Event consumer failed, retrying in %.0fs", delay)
        finally:
            await consumer.stop()
        await asyncio.sleep(delay)
        delay = min(delay * 2, MAX_BACKOFF)
