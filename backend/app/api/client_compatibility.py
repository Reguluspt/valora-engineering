"""Authenticated, read-only client contract metadata; no business authority."""

from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from app.core.rbac import get_current_user

router = APIRouter(prefix="/api/v1", tags=["client-compatibility"])


class ClientCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: Literal["valora.client-compat/1"] = "valora.client-compat/1"
    api_contract: Literal["valora.api/1"] = "valora.api/1"
    web_contract: Literal["valora.web/1"] = "valora.web/1"
    required_native_protocol: Literal["valora.native/2"] = "valora.native/2"
    minimum_client_compatibility: Literal[1] = 1
    recommended_client_compatibility: Literal[1] = 1


@router.get("/client-compatibility", response_model=ClientCompatibility,
            dependencies=[Depends(get_current_user)])
def read_client_compatibility(response: Response) -> ClientCompatibility:
    response.headers["Cache-Control"] = "no-store"
    return ClientCompatibility()
