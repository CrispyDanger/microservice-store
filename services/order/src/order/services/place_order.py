from uuid import UUID

from aiokafka import AIOKafkaProducer
from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC, OrderCreated
from order.models import Order, OrderItem
from order.schemas.order import OrderItemOutput, OrderOutput, PlaceOrderInput


async def place_order(
    data: PlaceOrderInput, user_id: UUID, producer: AIOKafkaProducer
) -> OrderOutput:
    async with in_transaction():
        order = await Order.create(user_id=user_id, total=data.total)
        items = [
            OrderItem(order=order, product_id=item.product_id, quantity=item.quantity)
            for item in data.items
        ]
        await OrderItem.bulk_create(items)

    event = OrderCreated(
        order_id=str(order.id), user_id=user_id, items=data.items, total=order.total
    )
    key, value = event.to_kafka()
    await producer.send_and_wait(ORDERS_TOPIC, key=key, value=value)

    return OrderOutput(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total=order.total,
        cancel_reason=order.cancel_reason,
        items=[OrderItemOutput.model_validate(item) for item in items],
        created_at=order.created_at,
    )
