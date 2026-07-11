from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.master_data import router as master_data_router
from app.api.projects import router as projects_router
from app.api.taxonomy import router as taxonomy_router
from app.api.asset_identity import router as asset_identity_router
from app.api.evidence import router as evidence_router
from app.api.knowledge import router as knowledge_router
from app.api.workflow import router as workflow_router
from app.api.workbench import router as workbench_router
from app.api.document_engine import router as document_engine_router
from app.api.document_intelligence import router as document_intelligence_router
from app.api.auth import router as auth_router, csrf_gate
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.valora_log_level)

# Handle Swagger/ReDoc and OpenAPI routes restriction in production env
is_prod = settings.valora_env == "production"

app = FastAPI(
    title="Valora API",
    version="0.0.1-sprint-0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
    dependencies=[Depends(csrf_gate)],
)

# Configure CORS Middleware safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(master_data_router)
app.include_router(projects_router)
app.include_router(taxonomy_router)
app.include_router(asset_identity_router)
app.include_router(evidence_router)
app.include_router(knowledge_router)
app.include_router(workflow_router)
app.include_router(workbench_router)
app.include_router(document_engine_router)
app.include_router(document_intelligence_router)
app.include_router(auth_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "valora-backend",
        "status": "ok",
        "phase": "engineering-sprint-0",
    }
