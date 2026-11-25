from tortoise import migrations
from tortoise.migrations import operations as ops
from payment.models.payment import PaymentStatus
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Payment',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('order_id', fields.UUIDField(unique=True)),
                ('amount', fields.DecimalField(max_digits=12, decimal_places=2)),
                ('status', fields.CharEnumField(description='SUCCEEDED: succeeded\nFAILED: failed\nREFUNDED: refunded', enum_type=PaymentStatus, max_length=9)),
                ('failure_reason', fields.CharField(null=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'payments', 'app': 'payment', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
