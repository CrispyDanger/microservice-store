from decimal import Decimal
from uuid import UUID

from payment.config import settings


class PaymentDeclined(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class FakeGateway:
    def __init__(self, decline_over: Decimal) -> None:
        self.decline_over = decline_over
        self.charges: dict[UUID, Decimal] = {}

    async def charge(self, idempotency_key: UUID, amount: Decimal) -> None:
        if amount > self.decline_over:
            raise PaymentDeclined(f"amount {amount} is over the limit of {self.decline_over}")
        self.charges.setdefault(idempotency_key, amount)


gateway = FakeGateway(decline_over=settings.decline_over)
