from tortoise import fields, models


class Event(models.Model):
    id = fields.UUIDField(primary_key=True)
    topic = fields.CharField(max_length=255)
    key = fields.CharField(max_length=255)
    payload = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)
    published_at = fields.DatetimeField(null=True)

    class Meta:
        table = "events"
        ordering = ["created_at"]
        indexes = (("published_at", "created_at"),)
