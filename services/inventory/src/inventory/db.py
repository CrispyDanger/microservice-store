from inventory.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "inventory": {
            "models": ["inventory.models"],
            "default_connection": "default",
            "migrations": "inventory.migrations",
        },
    },
    "use_tz": True,
    "timezone": "UTC",
}
