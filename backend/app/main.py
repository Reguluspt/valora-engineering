from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.master_data import router as master_data_router
from app.api.projects import router as projects_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.valora_log_level)

app = FastAPI(
    title="Valora API",
    version="0.0.1-sprint-0",
    docs_url="/docs" if settings.valora_env != "production" else None,
)

app.include_router(health_router)
app.include_router(master_data_router)
app.include_router(projects_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "valora-backend",
        "status": "ok",
        "phase": "engineering-sprint-0",
    }
