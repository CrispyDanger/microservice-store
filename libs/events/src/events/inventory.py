from typing import Literal

from events.base import Event

INVENTORY_TOPIC = "inventory"


class StockReserved(Event):
    type: Literal["StockReserved"] = "StockReserved"


class StockRejected(Event):
    type: Literal["StockRejected"] = "StockRejected"
    reason: str
