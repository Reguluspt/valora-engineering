from worker.config import get_worker_settings


def test_worker_settings_load() -> None:
    settings = get_worker_settings()
    assert settings.valora_env
