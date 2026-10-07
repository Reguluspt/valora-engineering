"""A14 safe read presentation; commands and completion remain A13 authority."""
import pytest

from app.modules.project_master_data.models import Supplier
from tests.test_g2_supplier_quotes_api import (  # noqa: F401
    entry_db, line_db, workbench_db, evidence_db, covered_db, quote_db, drafted_db, http_client,
)
from tests.test_g2_supplier_quotes import request_for


def test_readable_projection_scope_decimal_and_no_sensitive_metadata(http_client):  # noqa: F811
    client, db, entry = http_client
    base = f'/api/v1/projects/{entry["project"].id}/supplier-quotes'
    suppliers = client.get(base + "/suppliers").json()
    supplier = suppliers["items"][0]
    assert supplier["legal_name"] == "Synthetic supplier"
    assert set(supplier) == {"supplier_id", "row_version", "legal_name", "display_name"}
    sources = client.get(base + "/sources").json()
    source = sources["items"][0]
    assert source["title"] == "Synthetic source"
    assert source["document_type"] == "supplier_quote"
    assert source["revision_number"] == 1 and source["available"]
    assert set(source) == {"quote_id", "source_revision_id", "title", "document_type", "revision_number",
        "generation", "sha256", "byte_length", "available"}
    prep = client.get(base + "/preparation").json()
    assert len(prep["lines"]) == len(prep["line_versions"]) == 3
    assert all(isinstance(line["quantity"], str) and line["asset_name"] and line["unit"] for line in prep["lines"])
    assert all(c["deficient"] and c["supplier_count"] == 0 for c in prep["coverage"])
    draft = client.get(base).json()["items"][0]
    assert draft["supplier"] == {"display_name": None, "legal_name": "Synthetic supplier"}
    assert draft["supplier_row_version"] == entry["quote_supplier"].row_version
    assert draft["coverage_line_ids"] == []
    confirmed = client.post(base + "/confirm", json=request_for(db, entry, "confirmation"))
    assert confirmed.status_code == 200, confirmed.text
    quote = client.get(base).json()["items"][0]
    assert quote["current_head"] and quote["eligible"]
    assert set(quote["coverage_line_ids"]) == {line["line_id"] for line in prep["lines"]}
    for response in (client.get(base), client.get(base + "/sources"), client.get(base + "/suppliers")):
        assert entry["quote_binding"].object_key not in response.text
        assert entry["quote_supplier"].tax_code not in response.text
        assert "contact_email" not in response.text and "object_key" not in response.text


def test_unavailable_source_keeps_label_and_explicit_availability(http_client):  # noqa: F811
    client, db, entry = http_client
    entry["quote_store"]._objects.clear()
    source = client.get(f'/api/v1/projects/{entry["project"].id}/supplier-quotes/sources').json()["items"][0]
    assert source["title"] == "Synthetic source" and source["available"] is False


@pytest.mark.parametrize("fault,result,reason", [
    ("source", "STALE", "source_not_current"),
    ("supplier", "BLOCKED", "supplier_identity_ambiguous"),
])
def test_case_state_serializes_existing_quote_diagnostics(http_client, fault, result, reason):  # noqa: F811
    client, db, entry = http_client
    base = f'/api/v1/projects/{entry["project"].id}'
    confirmed = client.post(base + "/supplier-quotes/confirm", json=request_for(db, entry, "confirmation"))
    assert confirmed.status_code == 200, confirmed.text
    if fault == "source":
        entry["quote_store"]._objects.clear()
    else:
        entry["quote_supplier"].tax_code = None
        db.add(Supplier(organization_id=entry["org"].id, legal_name=entry["quote_supplier"].legal_name,
            status="active", tax_code=None, created_by=entry["user"].id))
        db.commit()
    response = client.get(base + "/case-state")
    assert response.status_code == 200, response.text
    case = response.json()
    prep = client.get(base + "/supplier-quotes/preparation").json()
    assert case["case_version"] == prep["case_version"]
    assert case["stages"][7]["result"] == prep["result"] == result
    assert {"stage": "SUPPLIER_QUOTES", "reason_code": reason} in case["stages"][7]["diagnostics"]
    assert all(stage["result"] == "NOT_AVAILABLE" for stage in case["stages"][8:])
    assert all(row["supplier_count"] == 0 for row in prep["coverage"])
    assert not any(secret in response.text for secret in (
        "Synthetic supplier", entry["quote_binding"].object_key, "unit_price", "contact_email",
    ))
