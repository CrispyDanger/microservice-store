from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from json import dumps, loads
from uuid import uuid4
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('order', '0003_auto_20261114_0213')]

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
            options={'table': 'events', 'app': 'order', 'indexes': [Index(fields=['published_at', 'created_at'])], 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
