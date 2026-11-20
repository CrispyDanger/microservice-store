from decimal import Decimal
from typing import Literal
from uuid import UUID

from events.base import Event

PAYMENTS_TOPIC = "payments"


class PaymentSucceeded(Event):
    type: Literal["PaymentSucceeded"] = "PaymentSucceeded"
    payment_id: UUID
    amount: Decimal


class PaymentFailed(Event):
    type: Literal["PaymentFailed"] = "PaymentFailed"
    reason: str
