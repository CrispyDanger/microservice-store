import asyncio
import os

from aiokafka import AIOKafkaConsumer

from events.orders import ORDERS_TOPIC

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


async def consume() -> None:
    consumer = AIOKafkaConsumer(
        ORDERS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="notifications",
        auto_offset_reset="earliest",  # a brand-new group starts from the oldest message
        enable_auto_commit=False,  # commit ourselves, after handling each message
    )
    await consumer.start()
    try:
        async for msg in consumer:
            # For now print everything. Later: only react to OrderConfirmed / OrderCancelled.
            key = msg.key.decode() if msg.key else None
            print(
                f"[notifications] partition={msg.partition} offset={msg.offset} "
                f"key={key} value={msg.value.decode()}",
                flush=True,
            )
            await consumer.commit()
    finally:
        await consumer.stop()


def main() -> None:
    asyncio.run(consume())
