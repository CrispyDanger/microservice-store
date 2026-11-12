from enum import StrEnum

from tortoise import fields, models
from tortoise.validators import MinValueValidator


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Order(models.Model):
    id = fields.UUIDField(primary_key=True)
    user_id = fields.UUIDField(db_index=True)
    status = fields.CharEnumField(OrderStatus, default=OrderStatus.PENDING)
    total = fields.DecimalField(max_digits=12, decimal_places=2)
    cancel_reason = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    items: fields.ReverseRelation["OrderItem"]

    def __str__(self):
        return str(self.id)

    class Meta:
        table = "orders"
        ordering = ["-created_at"]


class OrderItem(models.Model):
    """One line of one order: a snapshot taken when the order is placed."""

    id = fields.UUIDField(primary_key=True)
    order = fields.ForeignKeyField(
        "order.Order", related_name="items", on_delete=fields.CASCADE
    )
    product_id = fields.UUIDField()
    quantity = fields.IntField(validators=[MinValueValidator(1)])

    class Meta:
        table = "order_items"
        unique_together = (("order", "product_id"),)
