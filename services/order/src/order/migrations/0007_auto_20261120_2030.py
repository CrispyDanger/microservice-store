from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('order', '0006_auto_20261120_0109')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='IdempotencyKey',
            name='created_at',
            field=fields.DatetimeField(db_index=True, auto_now=False, auto_now_add=True),
        ),
        ops.AlterField(
            model_name='ProcessedEvent',
            name='processed_at',
            field=fields.DatetimeField(db_index=True, auto_now=False, auto_now_add=True),
        ),
    ]
