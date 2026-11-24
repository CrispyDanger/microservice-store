from enum import StrEnum

from tortoise import fields, models


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(models.Model):
    id = fields.UUIDField(primary_key=True)
    order_id = fields.UUIDField(unique=True)
    amount = fields.DecimalField(max_digits=12, decimal_places=2)
    status = fields.CharEnumField(PaymentStatus, default=PaymentStatus.PENDING)
    failure_reason = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "payments"
