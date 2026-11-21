from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="INVENTORY_")

    database_url: str
    jwt_public_key_path: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", validation_alias="KAFKA_BOOTSTRAP_SERVERS"
    )


settings = Settings()
