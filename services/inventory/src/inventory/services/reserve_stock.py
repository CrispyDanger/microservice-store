import logging
from decimal import Decimal
from uuid import UUID

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from events.inventory import INVENTORY_TOPIC, ReservedItem, StockRejected, StockReserved
from events.orders import OrderCreated
from inventory.models import (
    ProcessedEvent,
    Product,
    StockReservation,
    StockReservationItem,
    StockReservationStatus,
)
from inventory.publishing import record_event

logger = logging.getLogger(__name__)


def _requested_quantities(event: OrderCreated) -> dict[UUID, int]:
    quantities: dict[UUID, int] = {}
    for item in event.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    return quantities


def _rejection_reason(quantities: dict[UUID, int], products: dict[UUID, Product]) -> str | None:
    for product_id, quantity in quantities.items():
        product = products.get(product_id)
        if product is None:
            return f"unknown product {product_id}"
        if product.stock < quantity:
            return (
                f"not enough stock for product {product_id}: "
                f"requested {quantity}, available {product.stock}"
            )
    return None


async def _reject(event: OrderCreated, reason: str) -> None:
    await StockReservation.create(
        order_id=event.order_id, status=StockReservationStatus.REJECTED, reject_reason=reason
    )
    await record_event(INVENTORY_TOPIC, StockRejected(order_id=event.order_id, reason=reason))


async def _reserve(event: OrderCreated, quantities: dict[UUID, int], products: list[Product]):
    items = [
        ReservedItem(product_id=p.id, quantity=quantities[p.id], unit_price=p.price)
        for p in products
    ]
    total = sum((item.unit_price * item.quantity for item in items), Decimal(0))

    reservation = await StockReservation.create(
        order_id=event.order_id, status=StockReservationStatus.RESERVED, total=total
    )
    await StockReservationItem.bulk_create(
        [
            StockReservationItem(
                reservation=reservation,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in items
        ]
    )
    for product in products:
        product.stock -= quantities[product.id]
        await product.save(update_fields=["stock", "updated_at"])

    await record_event(
        INVENTORY_TOPIC, StockReserved(order_id=event.order_id, items=items, total=total)
    )


async def reserve_stock(event: OrderCreated) -> None:
    quantities = _requested_quantities(event)
    try:
        async with in_transaction():
            await ProcessedEvent.create(event_id=event.event_id)
            products = await (
                Product.filter(id__in=list(quantities)).order_by("id").select_for_update()
            )
            reason = _rejection_reason(quantities, {p.id: p for p in products})
            if reason is None:
                await _reserve(event, quantities, products)
            else:
                await _reject(event, reason)
    except IntegrityError:
        logger.info("Duplicate event %s skipped", event.event_id)
