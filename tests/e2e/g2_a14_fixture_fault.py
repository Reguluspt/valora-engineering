"""External synthetic fault setup, never an application operation or new authority."""
import argparse
import json
import os
import uuid
from pathlib import Path

from app.main import app  # Registers the existing model graph.
from app.db import SessionLocal
from app.modules.project_master_data.models import Project, OrganizationProfile, Supplier, AppraisedPriceDecision, NccSelectionRevision
from app.modules.document_workspace.models import StorageObjectBinding
from app.modules.project_master_data.supplier_quote_models import SupplierQuoteFact, SupplierQuoteReceipt


def main():
    if os.environ.get("POSTGRES_DB") != "valora_a14":
        raise ValueError("Fault setup requires isolated valora_a14 database")
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("fault", choices=["counts", "missing", "corrupt", "inactive", "merged", "ambiguous"])
    args = parser.parse_args()
    with SessionLocal() as db:
        project = db.query(Project).filter_by(id=uuid.UUID(args.project)).one()
        org = db.query(OrganizationProfile).filter_by(id=project.organization_id).one()
        if not org.organization_slug.startswith("a14-synthetic"):
            raise ValueError("Only isolated A14 synthetic fixtures may be changed")
        if args.fault == "counts":
            print(json.dumps({"appraised_price_decisions": db.query(AppraisedPriceDecision).count(),
                "ncc_selection_revisions": db.query(NccSelectionRevision).count(),
                "quote_facts": db.query(SupplierQuoteFact).filter_by(project_id=project.id).count(),
                "quote_receipts": db.query(SupplierQuoteReceipt).filter_by(project_id=project.id).count()}))
            return
        issuer = db.query(Supplier).filter_by(organization_id=org.id, display_name="Thiết bị A14").one()
        if args.fault in ("inactive", "merged", "ambiguous"):
            if args.fault == "inactive":
                issuer.status = "inactive"
            else:
                target = Supplier(organization_id=org.id, legal_name=issuer.legal_name if args.fault == "ambiguous" else "NCC hợp nhất tổng hợp",
                    tax_code=None, status="active", created_by=issuer.created_by)
                db.add(target)
                db.flush()
                if args.fault == "merged":
                    issuer.merged_into_supplier_id = target.id
                else:
                    issuer.tax_code = None
            issuer.row_version += 1
            db.commit()
        else:
            # Every retained object in this dedicated project is synthetic.
            root = Path("/var/lib/valora/a14-blobs").resolve()
            if app.state.document_blob_store._root != root:
                raise ValueError("Unexpected synthetic blob root")
            for binding in db.query(StorageObjectBinding).filter_by(project_id=project.id, organization_id=org.id):
                path = (root / "objects" / binding.object_key).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError("Synthetic target must be a file inside its blob root")
                if args.fault == "missing":
                    path.unlink()
                else:
                    path.write_bytes(b"A14 synthetic corruption")
        print(json.dumps({"fault": args.fault, "project_id": str(project.id)}))


if __name__ == "__main__":
    main()
