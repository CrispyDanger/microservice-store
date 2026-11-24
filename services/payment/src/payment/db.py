from payment.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "payment": {
            "models": ["payment.models"],
            "default_connection": "default",
            "migrations": "payment.migrations",
        },
    },
    "use_tz": True,
    "timezone": "UTC",
}
