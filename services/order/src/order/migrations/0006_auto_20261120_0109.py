from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('order', '0005_auto_20261120_0019')]

    initial = False

    operations = [
        ops.AddIndex(
            model_name='Order',
            index=Index(fields=['status', 'created_at']),
        ),
    ]
