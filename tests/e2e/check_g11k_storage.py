"""Read-only PostgreSQL and configured object-store verification inside backend container."""

import hashlib
import json
import os
import uuid

from app.db import SessionLocal
from app.modules.excel_import import models as excel_import_models  # noqa: F401
from app.modules.excel_import.infrastructure.object_storage import get_object_storage
from app.modules.project_master_data.models import PreliminaryResultArtifact, ProjectOfficialIntakeCommit


def main():
    project_id = uuid.UUID(os.environ["G11K_PROJECT_ID"])
    db = SessionLocal()
    try:
        artifacts = db.query(PreliminaryResultArtifact).filter_by(project_id=project_id).all()
        commits = db.query(ProjectOfficialIntakeCommit).filter_by(project_id=project_id).all()
        assert len(artifacts) == len(commits) == 1, (len(artifacts), len(commits))
        artifact, commit = artifacts[0], commits[0]
        assert artifact.id == commit.preliminary_result_artifact_id
        assert artifact.organization_id == commit.organization_id
        assert artifact.content_checksum_sha256 == commit.preliminary_result_sha256
        assert artifact.source_snapshot_sha256 == commit.source_snapshot_sha256
        storage = get_object_storage()
        stat = storage.head(artifact.storage_object_key)
        assert stat and stat.size == artifact.file_size_bytes
        with storage.open_stream(artifact.storage_object_key) as stream:
            content = stream.read()
        assert len(content) == artifact.file_size_bytes
        assert hashlib.sha256(content).hexdigest() == artifact.content_checksum_sha256
        assert stat.content_type == artifact.content_type
        print(json.dumps({
            "project_id": str(project_id), "result_id": str(artifact.id), "intake_id": str(commit.id),
            "organization_id": str(artifact.organization_id), "result_version": artifact.version,
            "content_type": artifact.content_type, "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(), "store_type": type(storage).__name__,
            "storage_key_present_in_database": bool(artifact.storage_object_key),
            "result_count": len(artifacts), "intake_count": len(commits),
        }, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
