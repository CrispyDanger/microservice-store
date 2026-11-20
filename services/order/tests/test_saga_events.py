import json
from decimal import Decimal
from uuid import uuid4

import pytest
from tortoise.exceptions import IntegrityError

from events.inventory import StockRejected, StockReserved
from events.payments import PaymentFailed, PaymentSucceeded
from order.models import ProcessedEvent


@pytest.mark.parametrize(
    "event",
    [
        StockReserved(order_id=str(uuid4())),
        StockRejected(order_id=str(uuid4()), reason="out of stock"),
        PaymentSucceeded(order_id=str(uuid4()), payment_id=uuid4(), amount=Decimal("29.97")),
        PaymentFailed(order_id=str(uuid4()), reason="card declined"),
    ],
)
def test_saga_events_round_trip_through_kafka_bytes(event):
    key, value = event.to_kafka()

    assert key == event.order_id.encode()
    assert json.loads(value)["type"] == type(event).__name__
    assert type(event).model_validate_json(value) == event


async def test_an_event_can_be_marked_processed_only_once():
    event_id = uuid4()
    await ProcessedEvent.create(event_id=event_id)

    with pytest.raises(IntegrityError):
        await ProcessedEvent.create(event_id=event_id)
