from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from user.models.user import Role
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='User',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('email', fields.CharField(unique=True, max_length=255)),
                ('first_name', fields.CharField(max_length=255)),
                ('last_name', fields.CharField(max_length=255)),
                ('password', fields.CharField(max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('is_active', fields.BooleanField(default=True)),
                ('role', fields.CharEnumField(default=Role.USER, description='ADMIN: admin\nUSER: user', enum_type=Role, max_length=5)),
            ],
            options={'table': 'users', 'app': 'user', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='RefreshToken',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('user.User', source_field='user_id', db_constraint=True, to_field='id', related_name='refresh_tokens', on_delete=OnDelete.CASCADE)),
                ('token_hash', fields.CharField(unique=True, max_length=64)),
                ('expires_at', fields.DatetimeField(auto_now=False, auto_now_add=False)),
                ('revoked_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'refresh_tokens', 'app': 'user', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
