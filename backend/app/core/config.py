from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    valora_env: str = "local"
    valora_log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "valora"
    postgres_user: str = "valora"
    postgres_password: str = "valora_local_password"

    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "valora"
    s3_secret_access_key: str = "valora_local_password"
    s3_bucket: str = "valora-local"
    s3_region: str = "us-east-1"

    backend_cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
