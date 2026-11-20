import logging

from order.config import settings

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> None:
    logging.basicConfig(level=settings.log_level, format=FORMAT)
