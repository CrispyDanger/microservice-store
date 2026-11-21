import logging

from tortoise.exceptions import IntegrityError
from tortoise.expressions import F
from tortoise.transactions import in_transaction

from events.orders import OrderCancelled
from inventory.models import ProcessedEvent, Product, StockReservation, StockReservationStatus

logger = logging.getLogger(__name__)


async def release_stock(event: OrderCancelled) -> None:
    try:
        async with in_transaction():
            await ProcessedEvent.create(event_id=event.event_id)
            reservation = await StockReservation.select_for_update().get_or_none(
                order_id=event.order_id
            )
            if reservation is None or reservation.status != StockReservationStatus.RESERVED:
                logger.info("Nothing to release for order %s", event.order_id)
                return

            items = await reservation.items.all().order_by("product_id")
            for item in items:
                await Product.filter(id=item.product_id).update(
                    stock=F("stock") + item.quantity
                )
            reservation.status = StockReservationStatus.RELEASED
            await reservation.save(update_fields=["status", "updated_at"])
    except IntegrityError:
        logger.info("Duplicate event %s skipped", event.event_id)
