from tortoise import migrations
from tortoise.migrations import operations as ops
from order.models.order import OrderStatus
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Order',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4,
                                        unique=True, db_index=True)),
                ('user_id', fields.UUIDField(db_index=True)),
                ('status', fields.CharEnumField(default=OrderStatus.PENDING,
                                                description='PENDING: pending\nCONFIRMED: confirmed\nCANCELLED: cancelled',
                                                enum_type=OrderStatus,
                                                max_length=9)),
                ('total', fields.DecimalField(max_digits=12, decimal_places=2)),
                ('cancel_reason', fields.CharField(null=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False,
                                                    auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True,
                                                    auto_now_add=False)),
            ],
            options={'table': 'orders', 'app': 'order', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='OrderItem',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('order', fields.ForeignKeyField('order.Order', source_field='order_id', db_constraint=True, to_field='id', related_name='items', on_delete=OnDelete.CASCADE)),
                ('product_id', fields.UUIDField()),
                ('quantity', fields.IntField()),
            ],
            options={'table': 'order_items', 'app': 'order', 'unique_together': (('order', 'product_id'),), 'pk_attr': 'id', 'table_description': 'One line of one order: a snapshot taken when the order is placed.'},
            bases=['Model'],
        ),
    ]
