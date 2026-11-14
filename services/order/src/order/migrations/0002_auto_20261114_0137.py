from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('order', '0001_initial')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='Order',
            name='user_id',
            field=fields.UUIDField(),
        ),
        ops.AddIndex(
            model_name='Order',
            index=Index(fields=['user_id', 'created_at', 'id']),
        ),
    ]
