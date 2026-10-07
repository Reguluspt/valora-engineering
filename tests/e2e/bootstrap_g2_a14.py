"""Migrated synthetic A14 dossier, real upstream commands and retained local bytes.

Run inside the isolated Linux backend; never point at a production database.
Only initial fixture setup uses these internal helpers. Browser quotation actions
use the production HTTP routes, authentication, CAS and PostgreSQL journal.
"""
import json
import os

from fastapi import Response
from app.db import SessionLocal
from app.main import app
from app.core.security import hash_password
from app.api.workbench import create_session
from app.modules.project_master_data.workbench_schemas import WorkbenchSessionCreate
from app.modules.project_master_data.models import Role, User, UserRole, Supplier, Currency
from app.modules.excel_import.infrastructure.object_storage import get_object_storage
from tests.g2_asset_review_helpers import seed_guarded_entry
from tests.test_g2_authority import _ready, _apply
from tests.test_g2_asset_workbench import snapshot, accept_all, human_commit, commit_saved, execute as wb_execute, request_for as wb_request
from tests.test_g2_price_evidence import execute as pe_execute, request_for as pe_request, cover_all
from tests.test_g2_supplier_quotes import retain, draft_all, execute as quote_execute, request_for as quote_request


def main():
    if os.environ.get("POSTGRES_DB") != "valora_a14":
        raise ValueError("A14 bootstrap requires its isolated valora_a14 database")
    password = os.environ["A14_SYNTHETIC_PASSWORD"]
    storage = get_object_storage()
    storage.ensure_bucket()
    with SessionLocal() as db:
        entry = seed_guarded_entry(db, storage=storage)
        org, user, project = entry["org"], entry["user"], entry["project"]
        org.organization_slug = os.environ.get("A14_SYNTHETIC_SLUG", "a14-synthetic")
        org.legal_name = "Đơn vị tổng hợp A14"
        user.email = "operator@a5.invalid"
        user.full_name = "Người kiểm thử A14"
        user.password_hash = hash_password(password)
        project.code = "A14-SYNTH-001"
        project.name = "Hồ sơ tổng hợp A14 — Báo giá NCC"
        for grant in db.query(UserRole).filter_by(user_id=user.id).all():
            db.delete(grant)
        db.flush()
        db.delete(entry["role"])
        owner, viewer = (db.query(Role).filter_by(code=code).one() for code in ("owner", "viewer"))
        db.add(UserRole(user_id=user.id, role_id=owner.id, is_active=True))
        reader = User(organization_id=org.id, email="viewer@a5.invalid", full_name="Người xem A14",
            password_hash=hash_password(password), status="active")
        db.add(reader)
        db.flush()
        db.add(UserRole(user_id=reader.id, role_id=viewer.id, is_active=True))
        db.commit()
        _apply(db, entry, _ready(db, entry))
        db.commit()
        session = create_session(WorkbenchSessionCreate(project_id=project.id), Response(), db, user)
        entry.update(session=session, line_id=snapshot(db, entry).lines[0].id)
        currency = db.query(Currency).filter_by(code="VND").first()
        if not currency:
            currency = Currency(code="VND", display_name="Đồng Việt Nam", status="active", decimal_places=0)
            db.add(currency)
            db.flush()
        for line in snapshot(db, entry).lines:
            line.appraised_currency_id = currency.id
        db.commit()
        # Establish initial working-price facts through the existing Human Commit.
        # No supplier-quotation action subsequently writes any working price.
        for index, line in enumerate(snapshot(db, entry).lines):
            entry["line_id"] = line.id
            version = human_commit(db, entry, "description", f"Thiết bị tổng hợp dòng {index + 1}; cùng cơ sở đơn vị")
            commit_saved(db, entry, "description", version)
            db.commit()
            if index < 2:
                price = "0" if index == 0 and os.environ.get("A14_ZERO_WORKING_FIXTURE") == "1" else "1000000"
                version = human_commit(db, entry, "appraised_unit_price", price)
                commit_saved(db, entry, "appraised_unit_price", version)
                db.commit()
        accept_all(db, entry)
        wb_execute(db, entry, wb_request(db, entry))
        db.commit()
        pe_execute(db, entry, pe_request(db, entry))
        db.commit()
        cover_all(db, entry)
        pe_execute(db, entry, pe_request(db, entry, "confirmation"))
        db.commit()
        if not db.query(Currency).filter_by(code="VND").first():
            db.add(Currency(code="VND", display_name="Đồng Việt Nam", status="active", decimal_places=0))
        issuer = Supplier(organization_id=org.id, legal_name="Công ty Thiết bị Tổng hợp A14", display_name="Thiết bị A14",
            status="active", tax_code="A14-SYNTHETIC", created_by=user.id)
        db.add(issuer)
        db.commit()
        retained = [retain(db, entry, app.state.document_blob_store, label=f"A14 retained synthetic supplier quotation {n}") for n in (1, 2)]
        db.commit()
        if os.environ.get("A14_CONFIRMED_FIXTURE") == "1":
            entry.update(quote_binding=retained[0], quote_supplier=issuer, quote_store=app.state.document_blob_store)
            db.info["supplier_quote_blob_store"] = app.state.document_blob_store
            draft_all(db, entry)
            quote_execute(db, entry, quote_request(db, entry, "confirmation"))
            db.commit()
        print(json.dumps({"project_id": str(project.id), "organization_slug": org.organization_slug, "supplier_id": str(issuer.id),
            "source_document_ids": [str(b.document_id) for b in retained], "source_revision_ids": [str(b.document_revision_id) for b in retained],
            "lines": [str(l.id) for l in snapshot(db, entry).lines], "fixture": "Migrated PostgreSQL / real MinIO / Linux immutable local document bytes"}))


if __name__ == "__main__":
    main()
