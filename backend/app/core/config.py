from functools import lru_cache
from typing import List

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
    cors_allow_credentials: bool = True
    app_secret_key: str = "valora-local-secret-key-change-this-in-production"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def parsed_cors_origins(self) -> List[str]:
        if not self.backend_cors_origins:
            return []
        origins = [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]
        # Empty wildcard security scanner check: block "*" in production env
        if self.valora_env == "production" and "*" in origins:
            raise ValueError(
                "Wildcard '*' is forbidden for CORS_ALLOWED_ORIGINS in production mode."
            )
        return origins

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
