from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    valora_env: str = "local"
    valora_log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
