from datetime import UTC, datetime, timedelta

from order.models import Event, IdempotencyKey, ProcessedEvent

PUBLISHED_EVENTS_RETENTION = timedelta(days=7)
PROCESSED_EVENTS_RETENTION = timedelta(days=14)
IDEMPOTENCY_KEYS_RETENTION = timedelta(hours=24)


async def purge_old_rows() -> int:
    now = datetime.now(UTC)
    events = await Event.filter(published_at__lt=now - PUBLISHED_EVENTS_RETENTION).delete()
    processed = await ProcessedEvent.filter(
        processed_at__lt=now - PROCESSED_EVENTS_RETENTION
    ).delete()
    keys = await IdempotencyKey.filter(created_at__lt=now - IDEMPOTENCY_KEYS_RETENTION).delete()
    return events + processed + keys
