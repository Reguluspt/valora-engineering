"""Bounded TXT-only custody routes; no professional quotation command."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from app.api.auth import get_current_session
from app.modules.document_workspace.application import quotation_document_import_service as service
from app.modules.document_workspace.quotation_document_import_schemas import (
    ImportCommand, RecoverCommand, MAX_BODY_BYTES, reject, validate_original,
)
from app.modules.project_master_data.models import UserSession

router = APIRouter()


def scope(project_id, session, request):
    return dict(org_id=session.organization_id, actor_id=session.user_id, session_id=session.id,
        project_id=project_id, blob_store=request.app.state.document_blob_store)


@router.get("/{project_id}/quotation-documents/import-context")
def context(project_id: uuid.UUID, request: Request, session: UserSession = Depends(get_current_session)):
    return service.import_context(**scope(project_id, session, request))


@router.get("/{project_id}/quotation-documents/import-receipts/{command_id}")
def receipt(project_id: uuid.UUID, command_id: uuid.UUID, request: Request, session: UserSession = Depends(get_current_session)):
    return service.read_status(**scope(project_id, session, request), command_id=command_id)


async def read_command(request, recover=False):
    if request.headers.get("content-encoding", "identity").lower() != "identity":
        reject(415, "txt_body_encoding_invalid")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "multipart/form-data":
        reject(415, "txt_multipart_required")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            reject(413, "txt_body_too_large")
        body.extend(chunk)

    async def bounded_body():
        yield bytes(body)

    form = None
    try:
        form = await MultiPartParser(request.headers, bounded_body(), max_files=1, max_fields=1, max_part_size=8192).parse()
        items = form.multi_items()
        if len(items) != 2 or {k for k, _ in items} != {"metadata", "file"}:
            reject(422, "txt_multipart_fields_invalid")
        metadata, file = form["metadata"], form["file"]
        if not isinstance(metadata, str) or len(metadata.encode("utf-8")) > 8192 or not isinstance(file, UploadFile):
            reject(422, "txt_multipart_fields_invalid")
        command = (RecoverCommand if recover else ImportCommand).model_validate_json(metadata)
        content = await file.read(1048577)
        return command, validate_original(file.filename, file.content_type, content)
    except (ValidationError, MultiPartException, ValueError, UnicodeError):
        reject(422, "txt_command_invalid")
    finally:
        if form is not None:
            await form.close()


async def dispatch(project_id, request, session, command_id=None):
    actor_scope = scope(project_id, session, request)
    command, original = await read_command(request, recover=command_id is not None)
    if command_id is not None and command.command_id != command_id:
        reject(409, "txt_command_mismatch")
    try:
        status, created = await run_in_threadpool(service.import_original, **actor_scope,
            command=command, original=original, recover=command_id is not None)
        return JSONResponse(status_code=201 if created else 200 if status["outcome"] == "finalized" else 202, content=status)
    except HTTPException:
        raise
    except Exception:
        return JSONResponse(status_code=503, content={"detail": {"error_code": "txt_outcome_unknown",
            "detail": "Chưa xác định được kết quả. Kiểm tra biên nhận của thao tác gốc trước khi tiếp tục."}})


@router.post("/{project_id}/quotation-documents/import")
async def import_txt(project_id: uuid.UUID, request: Request, session: UserSession = Depends(get_current_session)):
    return await dispatch(project_id, request, session)


@router.post("/{project_id}/quotation-documents/import-receipts/{command_id}/recover")
async def recover_txt(project_id: uuid.UUID, command_id: uuid.UUID, request: Request, session: UserSession = Depends(get_current_session)):
    return await dispatch(project_id, request, session, command_id)
