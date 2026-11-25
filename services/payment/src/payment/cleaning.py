import asyncio
import logging

from payment.services.clean_old_events import clean_old_events

logger = logging.getLogger(__name__)

INTERVAL = 3600.0


async def run_cleanup() -> None:
    while True:
        try:
            deleted = await clean_old_events()
            if deleted:
                logger.info("Deleted %d old rows", deleted)
        except Exception:
            logger.exception("Cleanup failed, retrying in %.0fs", INTERVAL)
        await asyncio.sleep(INTERVAL)
