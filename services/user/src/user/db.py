from user.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "user": {
            "models": ["user.models"],
            "default_connection": "default",
            "migrations": "user.migrations",
        },
    },
    "use_tz": True,
    "timezone": "UTC",
}
