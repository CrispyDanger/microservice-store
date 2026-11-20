from tortoise import fields, models


class ProcessedEvent(models.Model):
    event_id = fields.UUIDField(primary_key=True)
    processed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "processed_events"
