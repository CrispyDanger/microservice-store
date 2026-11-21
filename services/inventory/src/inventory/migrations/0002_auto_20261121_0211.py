from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from inventory.models.stock_reservation import StockReservationStatus
from json import dumps, loads
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('inventory', '0001_initial')]

    initial = False

    operations = [
        ops.CreateModel(
            name='Event',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('topic', fields.CharField(max_length=255)),
                ('key', fields.CharField(max_length=255)),
                ('payload', fields.JSONField(encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('published_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
            ],
            options={'table': 'events', 'app': 'inventory', 'indexes': [Index(fields=['published_at', 'created_at'])], 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='ProcessedEvent',
            fields=[
                ('event_id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('processed_at', fields.DatetimeField(db_index=True, auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'processed_events', 'app': 'inventory', 'pk_attr': 'event_id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='StockReservation',
            fields=[
                ('order_id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('status', fields.CharEnumField(description='RESERVED: reserved\nREJECTED: rejected\nRELEASED: released', enum_type=StockReservationStatus, max_length=8)),
                ('total', fields.DecimalField(null=True, max_digits=12, decimal_places=2)),
                ('reject_reason', fields.CharField(null=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'stock_reservations', 'app': 'inventory', 'pk_attr': 'order_id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='StockReservationItem',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('reservation', fields.ForeignKeyField('inventory.StockReservation', source_field='reservation_id', db_constraint=True, to_field='order_id', related_name='items', on_delete=OnDelete.CASCADE)),
                ('product', fields.ForeignKeyField('inventory.Product', source_field='product_id', db_constraint=True, to_field='id', on_delete=OnDelete.RESTRICT)),
                ('quantity', fields.IntField()),
                ('unit_price', fields.DecimalField(max_digits=12, decimal_places=2)),
            ],
            options={'table': 'stock_reservation_items', 'app': 'inventory', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
