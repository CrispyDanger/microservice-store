from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('order', '0002_auto_20261114_0137')]

    initial = False

    operations = [
        ops.CreateModel(
            name='IdempotencyKey',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user_id', fields.UUIDField()),
                ('key', fields.UUIDField()),
                ('request_hash', fields.CharField(max_length=64)),
                ('order', fields.ForeignKeyField('order.Order', source_field='order_id', db_constraint=True, to_field='id', on_delete=OnDelete.CASCADE)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'idempotency_keys', 'app': 'order', 'unique_together': (('user_id', 'key'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
