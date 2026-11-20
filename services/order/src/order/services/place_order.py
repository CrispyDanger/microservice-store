import hashlib
import json
from decimal import Decimal
from uuid import UUID

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC, OrderCreated
from order.exceptions import IdempotencyKeyReused
from order.models import IdempotencyKey, Order, OrderItem
from order.publishing import record_event
from order.schemas.order import OrderOutput, PlaceOrderInput


def hash_request(data: PlaceOrderInput) -> str:
    canonical = {
        "items": sorted(
            ({"product_id": str(i.product_id), "quantity": i.quantity} for i in data.items),
            key=lambda i: i["product_id"],
        ),
        "total": str(data.total.quantize(Decimal("0.01"))),
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


async def _check_idempotency(user_id: UUID, key: UUID, request_hash: str) -> OrderOutput | None:
    record = await IdempotencyKey.get_or_none(user_id=user_id, key=key)
    if record is None:
        return None
    if record.request_hash != request_hash:
        raise IdempotencyKeyReused()
    order = await Order.get(id=record.order_id).prefetch_related("items")
    return OrderOutput.model_validate(order)


async def place_order(data: PlaceOrderInput, user_id: UUID, idempotency_key: UUID) -> OrderOutput:
    request_hash = hash_request(data)
    try:
        async with in_transaction():
            order = await Order.create(user_id=user_id, total=data.total)
            items = [
                OrderItem(order=order, product_id=item.product_id, quantity=item.quantity)
                for item in data.items
            ]
            await OrderItem.bulk_create(items)
            await IdempotencyKey.create(
                user_id=user_id, key=idempotency_key, request_hash=request_hash, order=order
            )
            event = OrderCreated(
                order_id=order.id, user_id=user_id, items=data.items, total=order.total
            )
            await record_event(ORDERS_TOPIC, event)
    except IntegrityError:
        idemp_order = await _check_idempotency(user_id, idempotency_key, request_hash)
        if idemp_order is not None:
            return idemp_order
        raise

    await order.fetch_related("items")
    return OrderOutput.model_validate(order)
