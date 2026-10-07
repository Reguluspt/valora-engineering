"""Production routes, safe scoped reads and server-derived quote authority."""
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.rbac import get_current_user
from app.db import get_db
from app.db.session import get_case_state_db
from tests.test_g2_supplier_quotes import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, covered_db as _covered_db, quote_db as _quote_db,
    drafted_db as _drafted_db, request_for, counts,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db
evidence_db, covered_db, quote_db, drafted_db = _evidence_db, _covered_db, _quote_db, _drafted_db


@pytest.fixture
def http_client(drafted_db):
    db, entry = drafted_db
    def writer():
        yield db
    def reader():
        with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as read:
            read.info["supplier_quote_blob_store"] = entry["quote_store"]
            yield read
    prior_store = app.state.document_blob_store
    app.state.document_blob_store = entry["quote_store"]
    app.dependency_overrides[get_db] = writer
    app.dependency_overrides[get_case_state_db] = reader
    app.dependency_overrides[get_current_user] = lambda: entry["user"]
    try:
        with TestClient(app) as client:
            yield client, db, entry
    finally:
        app.state.document_blob_store = prior_store
        for dependency in (get_db, get_case_state_db, get_current_user):
            app.dependency_overrides.pop(dependency, None)


def test_http_click_case_state_safe_read_and_receipt(http_client):
    client, db, entry = http_client
    base = f'/api/v1/projects/{entry["project"].id}'
    case = client.get(base + "/case-state")
    assert case.status_code == 200, case.text
    state = case.json()
    assert state["current_stage"] == "SUPPLIER_QUOTES"
    assert state["next_action"]["semantic_route_key"] == "supplier_quotes_prepare_required"
    assert state["next_action"]["context"]["kind"] == "supplier_quotes_preparation"
    assert state["capabilities"][7]["provider_key"] == "supplier_quotes_v1"
    assert not any(term in case.text for term in ("Synthetic supplier", "123456789012345678", entry["quote_binding"].object_key))
    prep = client.get(base + "/supplier-quotes/preparation")
    assert prep.status_code == 200 and prep.json()["writable"]
    req = request_for(db, entry, "confirmation")
    rejected = client.post(base + "/supplier-quotes/confirm", json=dict(req, professional_checklist=True))
    assert rejected.status_code == 400
    result = client.post(base + "/supplier-quotes/confirm", json=req)
    assert result.status_code == 200, result.text
    before = counts(db)
    for _ in range(2):
        replay = client.post(base + "/supplier-quotes/confirm", json=req)
        assert replay.status_code == 200 and replay.json()["replayed"]
    receipt = client.get(base + "/supplier-quotes/command-receipts/" + req["command_id"])
    assert receipt.status_code == 200 and receipt.json()["result"] == result.json()["result"]
    complete = client.get(base + "/case-state")
    assert complete.status_code == 200, complete.text
    assert complete.json()["stages"][7]["result"] == "COMPLETE"
    assert complete.json()["next_action"]["kind"] == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
    assert all(s["result"] == "NOT_AVAILABLE" for s in complete.json()["stages"][8:])
    quotes = client.get(base + "/supplier-quotes")
    assert quotes.status_code == 200 and quotes.json()["items"][0]["eligible"]
    assert len(quotes.json()["items"][0]["items"]) == 3
    sources = client.get(base + "/supplier-quotes/sources")
    assert sources.status_code == 200 and sources.json()["items"][0]["available"]
    assert entry["quote_binding"].object_key not in sources.text
    assert counts(db) == before


def test_reads_access_scope_and_unavailable_writes(http_client):
    client, db, entry = http_client
    base = f'/api/v1/projects/{entry["project"].id}/supplier-quotes'
    assert client.get(base, params={"quote_id": str(uuid.uuid4())}).status_code == 404
    assert client.get(base, params={"revision_id": str(uuid.uuid4())}).status_code == 404
    assert client.get(base.replace(str(entry["project"].id), str(uuid.uuid4()))).status_code == 404
    assert client.get(base, params={"limit": 51}).status_code == 400
    entry["role"].permissions = ["project:read"]
    db.commit()
    assert client.get(base + "/preparation").status_code == 200
    assert not client.get(base + "/preparation").json()["writable"]
    assert client.post(base + "/confirm", json=request_for(db, entry, "confirmation")).status_code == 403
    entry["role"].permissions = []
    db.commit()
    assert client.get(base).status_code == 403
    def anonymous():
        raise HTTPException(401, detail="Not authenticated")
    app.dependency_overrides[get_current_user] = anonymous
    assert client.get(base).status_code == 401
