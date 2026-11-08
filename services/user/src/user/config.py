from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="USER_")

    database_url: str
    jwt_private_key_path: str
    jwt_public_key_path: str
    access_token_minutes: int
    refresh_token_days: int


settings = Settings()
