from tortoise import fields, models
from tortoise.validators import MinValueValidator


class Product(models.Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=255)
    price = fields.DecimalField(max_digits=12, decimal_places=2)
    stock = fields.IntField(default=0, validators=[MinValueValidator(0)])
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        table = "products"
        ordering = ["name"]
