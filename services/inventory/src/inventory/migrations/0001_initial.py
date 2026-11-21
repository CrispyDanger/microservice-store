from tortoise import migrations
from tortoise.migrations import operations as ops
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Product',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('name', fields.CharField(max_length=255)),
                ('price', fields.DecimalField(max_digits=12, decimal_places=2)),
                ('stock', fields.IntField(default=0)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'products', 'app': 'inventory', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
