from uuid import UUID, uuid4

from aiokafka import AIOKafkaProducer

from events.orders import ORDERS_TOPIC, OrderCreated
from order.schemas.order import PlaceOrderInput, PlaceOrderOutput


async def place_order(
    data: PlaceOrderInput, user_id: UUID, producer: AIOKafkaProducer
) -> PlaceOrderOutput:
    order_id = f"ord-{uuid4().hex[:8]}"
    # Next: save the order as PENDING in this service's own database first.
    # user_id will be a plain UUID column there, not a foreign key: users live in another DB.
    event = OrderCreated(
        order_id=order_id, user_id=user_id, items=data.items, total=data.total
    )
    key, value = event.to_kafka()
    await producer.send_and_wait(ORDERS_TOPIC, key=key, value=value)
    return PlaceOrderOutput(order_id=order_id, user_id=user_id, status="PENDING")
