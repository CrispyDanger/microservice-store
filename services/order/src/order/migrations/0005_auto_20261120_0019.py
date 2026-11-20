from tortoise import migrations
from tortoise.migrations import operations as ops
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('order', '0004_auto_20261116_2053')]

    initial = False

    operations = [
        ops.CreateModel(
            name='ProcessedEvent',
            fields=[
                ('event_id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('processed_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'processed_events', 'app': 'order', 'pk_attr': 'event_id'},
            bases=['Model'],
        ),
    ]
