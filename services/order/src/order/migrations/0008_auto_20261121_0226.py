from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('order', '0007_auto_20261120_2030')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='Order',
            name='total',
            field=fields.DecimalField(null=True, max_digits=12, decimal_places=2),
        ),
        ops.AddField(
            model_name='OrderItem',
            name='unit_price',
            field=fields.DecimalField(null=True, max_digits=12, decimal_places=2),
        ),
    ]
