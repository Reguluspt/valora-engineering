"""Read-only admission of existing retained document revisions; no ingestion."""
import asyncio
import hashlib
from datetime import timezone
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from app.core.config import get_settings
from app.modules.document_workspace.models import DocumentRevision, DocumentRevisionCurrentHead, StorageObjectBinding
from app.modules.document_workspace.infrastructure.document_blob_store_factory import build_document_blob_store


@lru_cache(maxsize=1)
def runtime_store():
    return build_document_blob_store(get_settings())


def run_storage(coroutine):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coroutine).result()


def retained_source(db, *, org_id, project_id, document_id, revision_id, locked=False):
    scope = dict(organization_id=org_id, project_id=project_id, document_id=document_id)
    head_query = db.query(DocumentRevisionCurrentHead).filter_by(**scope).populate_existing()
    revision_query = db.query(DocumentRevision).filter_by(**scope, id=revision_id).populate_existing()
    binding_query = db.query(StorageObjectBinding).filter_by(**scope, document_revision_id=revision_id).populate_existing()
    if locked:
        head_query = head_query.with_for_update(read=True)
        revision_query = revision_query.with_for_update(read=True)
        binding_query = binding_query.with_for_update(read=True)
    head, revision, binding = head_query.first(), revision_query.first(), binding_query.first()
    if not revision or not binding:
        return None, False
    proof = dict(binding_id=str(binding.id), revision_id=str(revision.id), document_id=str(document_id),
        organization_id=str(org_id), project_id=str(project_id), generation=revision.document_revision,
        sha256=binding.content_sha256, byte_length=binding.byte_length,
        target_sha256=hashlib.sha256((binding.storage_profile_id + "\n" + binding.container_name + "\n" + binding.object_key).encode()).hexdigest(),
        provider_version=binding.provider_object_version)
    proof["created_at"] = binding.object_created_at.astimezone(timezone.utc).isoformat()
    proof["current_revision_id"] = str(head.current_revision_id) if head else None
    proof["current_generation"] = head.document_revision if head else None
    store = db.info.get("supplier_quote_blob_store") or runtime_store()
    if (not head or head.current_revision_id != revision_id or head.document_revision != revision.document_revision
            or binding.content_sha256 != revision.content_checksum_sha256
            or binding.storage_profile_id != f"exchange-{store.provider_kind}"
            or binding.container_name != "valora-document-blobs" or binding.provider_kind != store.provider_kind
            or not binding.provider_object_version or binding.byte_length <= 0 or binding.byte_length > 32_000_000):
        return proof, False
    try:
        observation = run_storage(store.observe(object_key=binding.object_key))
        def observation_proof(observed):
            return dict(status=str(observed.status), byte_length=observed.byte_length,
                provider_version=observed.provider_object_version,
                created_at=observed.object_created_at.astimezone(timezone.utc).isoformat() if observed.object_created_at else None)
        proof["observation"] = observation_proof(observation)
        if (str(observation.status) != "PRESENT" or observation.byte_length != binding.byte_length
                or observation.provider_object_version != binding.provider_object_version or observation.object_created_at != binding.object_created_at):
            return proof, False
        verified = run_storage(store.read_verified(object_key=binding.object_key,
            expected_sha256=binding.content_sha256, expected_byte_length=binding.byte_length, max_bytes=32_000_000))
        proof["verification"] = dict(status=str(verified.status), sha256=verified.observed_sha256, byte_length=verified.observed_byte_length)
        after = run_storage(store.observe(object_key=binding.object_key))
        proof["after_observation"] = observation_proof(after)
        current = (str(observation.status) == "PRESENT" and observation.byte_length == binding.byte_length
            and observation.provider_object_version == binding.provider_object_version
            and str(verified.status) == "MATCH" and verified.observed_sha256 == binding.content_sha256
            and verified.observed_byte_length == binding.byte_length and str(after.status) == "PRESENT"
            and after.byte_length == binding.byte_length and after.provider_object_version == binding.provider_object_version
            and after.object_created_at == binding.object_created_at)
    except Exception:
        current = False
    return proof, current
