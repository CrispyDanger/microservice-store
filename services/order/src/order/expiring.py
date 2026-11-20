import asyncio
import logging
from datetime import timedelta

from order.config import settings
from order.services.expire_orders import BATCH_SIZE, expire_pending_orders

logger = logging.getLogger(__name__)

INTERVAL = 60.0


async def run_expiry() -> None:
    timeout = timedelta(minutes=settings.pending_timeout_minutes)
    while True:
        try:
            expired = await expire_pending_orders(timeout)
        except Exception:
            logger.exception("Order expiry failed, retrying in %.0fs", INTERVAL)
            expired = 0
        if expired:
            logger.info("Cancelled %d orders stuck in pending", expired)
        if expired < BATCH_SIZE:
            await asyncio.sleep(INTERVAL)
