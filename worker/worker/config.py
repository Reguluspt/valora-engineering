from functools import lru_cache
import socket

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    valora_env: str = "local"
    valora_log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    worker_id: str = Field(default_factory=lambda: f"worker-{socket.gethostname()}")
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0, le=60)
    worker_lease_duration_seconds: int = Field(default=300, ge=3, le=3600)
    worker_heartbeat_interval_seconds: float = Field(default=60.0, gt=0, le=1200)
    worker_retry_base_seconds: int = Field(default=5, ge=1, le=3600)

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
