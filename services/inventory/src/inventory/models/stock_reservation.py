from enum import StrEnum

from tortoise import fields, models
from tortoise.validators import MinValueValidator


class StockReservationStatus(StrEnum):
    RESERVED = "reserved"
    REJECTED = "rejected"
    RELEASED = "released"


class StockReservation(models.Model):
    order_id = fields.UUIDField(primary_key=True)
    status = fields.CharEnumField(StockReservationStatus)
    total = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    reject_reason = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    items: fields.ReverseRelation["StockReservationItem"]

    class Meta:
        table = "stock_reservations"


class StockReservationItem(models.Model):
    id = fields.UUIDField(primary_key=True)
    reservation = fields.ForeignKeyField(
        "inventory.StockReservation", related_name="items", on_delete=fields.CASCADE
    )
    product = fields.ForeignKeyField(
        "inventory.Product", related_name=None, on_delete=fields.RESTRICT
    )
    quantity = fields.IntField(validators=[MinValueValidator(1)])
    unit_price = fields.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        table = "stock_reservation_items"
