import json
from decimal import Decimal
from uuid import uuid4

import pytest
from tortoise.exceptions import IntegrityError

from events.inventory import ReservedItem, StockRejected, StockReserved
from events.payments import PaymentFailed, PaymentSucceeded
from order.models import ProcessedEvent


@pytest.mark.parametrize(
    "event",
    [
        StockReserved(
            order_id=uuid4(),
            items=[ReservedItem(product_id=uuid4(), quantity=3, unit_price=Decimal("9.99"))],
            total=Decimal("29.97"),
        ),
        StockRejected(order_id=uuid4(), reason="out of stock"),
        PaymentSucceeded(order_id=uuid4(), payment_id=uuid4(), amount=Decimal("29.97")),
        PaymentFailed(order_id=uuid4(), reason="card declined"),
    ],
)
def test_incoming_events_round_trip_through_json(event):
    value = event.model_dump_json().encode()

    assert json.loads(value)["type"] == type(event).__name__
    assert type(event).model_validate_json(value) == event


async def test_an_event_can_be_marked_processed_only_once():
    event_id = uuid4()
    await ProcessedEvent.create(event_id=event_id)

    with pytest.raises(IntegrityError):
        await ProcessedEvent.create(event_id=event_id)
