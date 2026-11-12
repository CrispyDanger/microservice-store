from order.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "order": {
            "models": ["order.models"],
            "default_connection": "default",
            "migrations": "order.migrations",
        },
    },
    "use_tz": True,
    "timezone": "UTC",
}
