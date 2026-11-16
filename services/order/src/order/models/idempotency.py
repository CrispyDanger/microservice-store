from tortoise import fields, models


class IdempotencyKey(models.Model):
    id = fields.UUIDField(primary_key=True)
    user_id = fields.UUIDField()
    key = fields.UUIDField()
    request_hash = fields.CharField(max_length=64)
    order = fields.ForeignKeyField("order.Order", related_name=None, on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "idempotency_keys"
        unique_together = (("user_id", "key"),)
