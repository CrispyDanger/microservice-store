import asyncio
import logging

from order.services.purge_old_rows import purge_old_rows

logger = logging.getLogger(__name__)

INTERVAL = 3600.0


async def run_cleanup() -> None:
    while True:
        try:
            deleted = await purge_old_rows()
            if deleted:
                logger.info("Deleted %d old rows", deleted)
        except Exception:
            logger.exception("Cleanup failed, retrying in %.0fs", INTERVAL)
        await asyncio.sleep(INTERVAL)
