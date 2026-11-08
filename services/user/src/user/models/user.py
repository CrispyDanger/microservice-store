from tortoise import fields, models
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class User(models.Model):
    id = fields.UUIDField(primary_key=True)
    email = fields.CharField(max_length=255, unique=True)
    first_name = fields.CharField(max_length=255)
    last_name = fields.CharField(max_length=255)
    password = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_active = fields.BooleanField(default=True)
    role = fields.CharEnumField(Role, default=Role.USER)
    refresh_tokens: fields.ReverseRelation["RefreshToken"]

    def __str__(self):
        return self.email

    class Meta:
        table = "users"
