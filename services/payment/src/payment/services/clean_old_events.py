from datetime import UTC, datetime, timedelta

from payment.models import Event, ProcessedEvent

PUBLISHED_EVENTS_RETENTION = timedelta(days=7)
PROCESSED_EVENTS_RETENTION = timedelta(days=14)


async def clean_old_events() -> int:
    now = datetime.now(UTC)
    events = await Event.filter(published_at__lt=now - PUBLISHED_EVENTS_RETENTION).delete()
    processed = await ProcessedEvent.filter(
        processed_at__lt=now - PROCESSED_EVENTS_RETENTION
    ).delete()
    return events + processed
