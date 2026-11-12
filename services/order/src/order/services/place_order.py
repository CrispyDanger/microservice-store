from uuid import UUID

from aiokafka import AIOKafkaProducer
from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC, OrderCreated
from order.models import Order, OrderItem
from order.schemas.order import OrderOutput, PlaceOrderInput


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

    await order.fetch_related("items")
    return OrderOutput.model_validate(order)
