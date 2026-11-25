from tortoise import migrations
from tortoise.migrations import operations as ops
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('payment', '0002_auto_20261124_2144')]

    initial = False

    operations = [
        ops.CreateModel(
            name='CancelledOrder',
            fields=[
                ('order_id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('cancelled_at', fields.DatetimeField(db_index=True, auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'cancelled_orders', 'app': 'payment', 'pk_attr': 'order_id'},
            bases=['Model'],
        ),
    ]
