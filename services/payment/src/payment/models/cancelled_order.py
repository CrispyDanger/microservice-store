from tortoise import fields, models


class CancelledOrder(models.Model):
    order_id = fields.UUIDField(primary_key=True)
    cancelled_at = fields.DatetimeField(auto_now_add=True, db_index=True)

    class Meta:
        table = "cancelled_orders"
