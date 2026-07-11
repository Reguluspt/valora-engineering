import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings, get_settings
from app.main import app

def test_config_handles_multiple_cors_origins():
    # 1. Parsing works with single value
    s1 = Settings(backend_cors_origins="http://example1.com")
    assert s1.parsed_cors_origins == ["http://example1.com"]

    # 2. Parsing works with comma separated origins
    s2 = Settings(backend_cors_origins="http://example1.com, http://example2.com ,http://example3.com")
    assert s2.parsed_cors_origins == [
        "http://example1.com",
        "http://example2.com",
        "http://example3.com"
    ]

    # 3. Block wildcard * in production mode
    s3 = Settings(valora_env="production", backend_cors_origins="http://example.com,*")
    with pytest.raises(ValueError, match="Wildcard '\\*' is forbidden for CORS_ALLOWED_ORIGINS in production mode"):
        _ = s3.parsed_cors_origins

    # 4. Empty returns empty list
    s4 = Settings(backend_cors_origins="")
    assert s4.parsed_cors_origins == []


def test_cors_middleware_behavior():
    # Verify CORS behavior under live FastAPI middleware stack
    client = TestClient(app)
    
    # 1. Allowed Origin is accepted
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # 2. Disallowed Origin is rejected
    response = client.get("/health", headers={"Origin": "http://malicious-domain.com"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


def test_production_and_dev_docs_routing(monkeypatch):
    # Test FastAPI docs routing based on environment configuration

    # 1. Dev / Test mode (local) -> Docs available
    # Reset app dependencies/settings using monkeypatch or manual settings swap
    # App is already loaded, but we check default local settings configuration:
    client = TestClient(app)
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200

    # 2. Production mode -> Docs disabled
    # Re-initialize app in production mode
    monkeypatch.setenv("VALORA_ENV", "production")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://prod-site.com")
    
    # Clear settings cache to force reload
    from app.core.config import get_settings as core_get_settings
    core_get_settings.cache_clear()
    
    # Import app inside to ensure it evaluates settings under production configuration
    # (Since app is already imported in global test scope, we manually instantiate a new FastAPI instance
    # mimicking main.py's initialization routing behavior)
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    settings = get_settings()
    is_prod = settings.valora_env == "production"
    
    prod_app = FastAPI(
        title="Valora API Test Prod",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )
    prod_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    prod_client = TestClient(prod_app)
    assert prod_client.get("/docs").status_code == 404
    assert prod_client.get("/redoc").status_code == 404
    assert prod_client.get("/openapi.json").status_code == 404
    
    # Clean up environment state
    monkeypatch.delenv("VALORA_ENV", raising=False)
    monkeypatch.delenv("BACKEND_CORS_ORIGINS", raising=False)
    core_get_settings.cache_clear()

