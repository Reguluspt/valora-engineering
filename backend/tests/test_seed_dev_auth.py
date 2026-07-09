import pytest
from app.core.config import Settings
from scripts.seed_dev_auth import seed_dev_auth

def test_seed_dev_auth_refuses_production(monkeypatch):
    # Verify seed script fails if env is set to production
    monkeypatch.setenv("VALORA_ENV", "production")
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    # We expect sys.exit(1)
    with pytest.raises(SystemExit) as excinfo:
        seed_dev_auth()
    assert excinfo.value.code == 1
    get_settings.cache_clear()
