"""A11 read projection must preserve A10 authority and disclosure boundaries."""
import uuid

from tests.test_g2_price_evidence_api import http_client as _http_client
from tests.test_g2_price_evidence import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, execute, request_for, snapshot, counts, cover_all, material,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db
evidence_db, http_client = _evidence_db, _http_client


def test_projection_registration_acceptance_and_set_truth(http_client):
    client, db, entry = http_client
    path = f'/api/v1/projects/{entry["project"].id}/price-evidence/workspace'
    line_id = snapshot(db, entry).lines[0].id
    def read():
        response = client.get(path, params={"line_id": str(line_id)})
        assert response.status_code == 200, response.text
        return response.json()
    first = read()
    assert first["covered_count"] == 0 and first["sealed_count"] == 3 and first["sources"] == []
    execute(db, entry, request_for(db, entry))
    db.commit()
    before = counts(db)
    registered = read()
    assert registered["covered_count"] == 0 and registered["sources"][0]["can_accept"]
    assert registered["sources"][0]["decision"] is None
    assert not {"reference", "retained_text", "value", "explanation", "historical"}.intersection(registered["sources"][0])
    assert counts(db) == before
    execute(db, entry, request_for(db, entry, "relevance", line_id=str(line_id)))
    db.commit()
    accepted = read()
    assert accepted["line_covered"] and accepted["covered_count"] == 1
    assert accepted["sources"][0]["decision"]["qualifying"]
    assert not accepted["confirmation_current"]
    other = snapshot(db, entry).lines[1].id
    assert not client.get(path, params={"line_id": str(other)}).json()["line_covered"]
    cover_all(db, entry)
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    complete = read()
    assert complete["confirmation_current"] and complete["can_withdraw_confirmation"]
    assert complete["covered_count"] == 3
    entry["project"].status = "archived"
    db.commit()
    readonly = read()
    assert readonly["confirmation_current"] and not readonly["can_withdraw_confirmation"]
    assert not any(readonly["sources"][0][key] for key in ("can_correct", "can_withdraw", "can_accept", "can_reject"))


def test_projection_revision_and_hold_are_not_inferred_by_client(http_client):
    client, db, entry = http_client
    execute(db, entry, request_for(db, entry))
    db.commit()
    req = request_for(db, entry, "relevance", outcome="rejected", disposition="unresolved_concern", reason_note="Synthetic concern")
    execute(db, entry, req)
    db.commit()
    source = next(iter(snapshot(db, entry).price_evidence.source_heads.values()))
    execute(db, entry, request_for(db, entry, "withdrawal", target_id=str(source.id)))
    db.commit()
    path = f'/api/v1/projects/{entry["project"].id}/price-evidence/workspace'
    result = client.get(path, params={"line_id": req["line_id"]}).json()
    assert result["line_hold"] and not result["line_covered"]
    assert result["sources"][0]["withdrawn"] and not result["sources"][0]["can_accept"]
    assert result["sources"][0]["can_reject"]
    execute(db, entry, request_for(db, entry, source_id=str(source.source_id), predecessor_revision_id=str(source.id),
                                 reason_note="Correct source", material=material(origin="Corrected publisher")))
    db.commit()
    result = client.get(path, params={"line_id": req["line_id"]}).json()
    assert result["sources"][0]["revision"] == 2 and result["line_hold"]
    assert result["sources"][0]["decision"]["evidence_revision_id"] == str(source.id)


def test_projection_scope_paging_and_access(http_client):
    client, db, entry = http_client
    path = f'/api/v1/projects/{entry["project"].id}/price-evidence/workspace'
    assert client.get(path, params={"line_id": str(uuid.uuid4())}).status_code == 404
    assert client.get(path.replace(str(entry["project"].id), str(uuid.uuid4()))).status_code == 404
    assert client.get(path, params={"limit": 51}).status_code == 400
    for _ in range(2):
        execute(db, entry, request_for(db, entry))
        db.commit()
    page = client.get(path, params={"limit": 1}).json()
    second = client.get(path, params={"limit": 1, "offset": page["next_offset"]}).json()
    assert len(page["sources"]) == len(second["sources"]) == 1 and second["next_offset"] is None
    assert page["sources"][0]["source_id"] != second["sources"][0]["source_id"]
    entry["role"].permissions = []
    db.commit()
    assert client.get(path).status_code == 403
