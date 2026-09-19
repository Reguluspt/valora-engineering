"""Create durable local fake-storage execution persistence.

Revision ID: b7c8d9e0f1a2
Revises: a6d9e4c2b8f1
Create Date: 2026-09-19 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a6d9e4c2b8f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sha256_check(column: str) -> str:
    return (
        f"length({column}) = 64 AND {column} = lower({column}) "
        f"AND {column} ~ '^[0-9a-f]{{64}}$'"
    )


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_document_revision_content_checksum",
        "document_revisions",
        ["organization_id", "project_id", "document_id", "id", "content_checksum_sha256"],
    )
    op.create_table(
        "document_storage_execution_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("expected_revision_id", sa.Uuid(), nullable=False),
        sa.Column("expected_document_revision", sa.Integer(), nullable=False),
        sa.Column("expected_content_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("plan_digest_sha256", sa.String(64), nullable=False),
        sa.Column("decision_digest_sha256", sa.String(64), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_storage_intent_idempotency"),
        sa.UniqueConstraint("organization_id", "id", name="uq_storage_intent_tenant_id"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            ["document_records.organization_id", "document_records.project_id", "document_records.id"],
            name="fk_storage_intent_document_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id", "expected_revision_id"],
            [
                "document_revisions.organization_id", "document_revisions.project_id",
                "document_revisions.document_id", "document_revisions.id",
            ],
            name="fk_storage_intent_revision_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "requested_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_storage_intent_actor_tenant", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("expected_document_revision > 0", name="chk_storage_intent_revision"),
        sa.CheckConstraint("length(trim(idempotency_key)) > 0", name="chk_storage_intent_idempotency"),
        sa.CheckConstraint(_sha256_check("expected_content_sha256"), name="chk_storage_intent_content"),
        sa.CheckConstraint(_sha256_check("request_digest_sha256"), name="chk_storage_intent_request"),
        sa.CheckConstraint(_sha256_check("plan_digest_sha256"), name="chk_storage_intent_plan"),
        sa.CheckConstraint(_sha256_check("decision_digest_sha256"), name="chk_storage_intent_decision"),
    )
    op.create_index(
        "idx_storage_intent_document", "document_storage_execution_intents",
        ["organization_id", "project_id", "document_id"],
    )
    op.create_table(
        "document_storage_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("execution_intent_id", sa.Uuid(), nullable=False),
        sa.Column("storage_profile_id", sa.String(64), nullable=False),
        sa.Column("provider_kind", sa.String(32), nullable=False),
        sa.Column("container_name", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("generator_version", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "execution_intent_id", name="uq_storage_candidate_intent"),
        sa.UniqueConstraint("organization_id", "id", name="uq_storage_candidate_tenant_id"),
        sa.UniqueConstraint("storage_profile_id", "container_name", "object_key", name="uq_storage_candidate_target"),
        sa.UniqueConstraint(
            "organization_id", "id", "content_sha256", "byte_length",
            name="uq_storage_candidate_integrity",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_candidate_intent_tenant", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("provider_kind IN ('fake')", name="chk_storage_candidate_provider"),
        sa.CheckConstraint("byte_length >= 0", name="chk_storage_candidate_size"),
        sa.CheckConstraint(
            "length(trim(storage_profile_id)) > 0 AND length(trim(container_name)) > 0 "
            "AND length(trim(object_key)) > 0 AND length(trim(media_type)) > 0 "
            "AND length(trim(generator_version)) > 0",
            name="chk_storage_candidate_identity",
        ),
        sa.CheckConstraint(_sha256_check("content_sha256"), name="chk_storage_candidate_content"),
    )
    op.create_table(
        "document_storage_execution_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("execution_intent_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_code", sa.String(64), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=True),
        sa.Column("provider_request_id", sa.String(255), nullable=True),
        sa.Column("observed_object_version", sa.String(255), nullable=True),
        sa.Column("observed_etag", sa.String(512), nullable=True),
        sa.Column("observed_object_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_content_sha256", sa.String(64), nullable=True),
        sa.Column("observed_byte_length", sa.BigInteger(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "execution_intent_id", "sequence", name="uq_storage_event_sequence"),
        sa.ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_event_intent_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "recorded_by_user_id"], ["users.organization_id", "users.id"],
            name="fk_storage_event_actor_tenant", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("sequence > 0", name="chk_storage_event_sequence"),
        sa.CheckConstraint("length(trim(event_code)) > 0", name="chk_storage_event_code"),
        sa.CheckConstraint("observed_byte_length IS NULL OR observed_byte_length >= 0", name="chk_storage_event_size"),
        sa.CheckConstraint(
            "observed_content_sha256 IS NULL OR (" + _sha256_check("observed_content_sha256") + ")",
            name="chk_storage_event_content",
        ),
    )
    op.create_table(
        "document_storage_execution_states",
        sa.Column("execution_intent_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("current_state", sa.String(48), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("last_event_sequence", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("execution_intent_id"),
        sa.ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_state_intent_tenant", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("state_version > 0", name="chk_storage_state_version"),
        sa.CheckConstraint("last_event_sequence > 0", name="chk_storage_state_sequence"),
        sa.CheckConstraint(
            "current_state IN ('PREPARED', 'CANDIDATE_GENERATED', 'CREATE_DISPATCHED', "
            "'CREATE_OUTCOME_UNKNOWN', 'OBJECT_OBSERVED', 'OBJECT_VERIFIED', 'FINALIZING', "
            "'STORAGE_UNAVAILABLE', 'RECONCILIATION_REQUIRED', 'SUPERSEDED', 'ABANDONED', 'FINALIZED')",
            name="chk_storage_state_value",
        ),
    )
    op.create_table(
        "storage_object_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_revision_id", sa.Uuid(), nullable=False),
        sa.Column("execution_intent_id", sa.Uuid(), nullable=False),
        sa.Column("storage_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("storage_profile_id", sa.String(64), nullable=False),
        sa.Column("provider_kind", sa.String(32), nullable=False),
        sa.Column("container_name", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False),
        sa.Column("provider_object_version", sa.String(255), nullable=True),
        sa.Column("checksum_algorithm", sa.String(16), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("observed_etag", sa.String(512), nullable=True),
        sa.Column("object_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("retention_policy_code", sa.String(64), nullable=False),
        sa.Column("retention_anchor_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("minimum_retain_until", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "document_revision_id", name="uq_storage_binding_revision"),
        sa.UniqueConstraint("organization_id", "execution_intent_id", name="uq_storage_binding_intent"),
        sa.UniqueConstraint("organization_id", "storage_candidate_id", name="uq_storage_binding_candidate"),
        sa.UniqueConstraint("storage_profile_id", "container_name", "object_key", name="uq_storage_binding_target"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id", "document_revision_id", "content_sha256"],
            [
                "document_revisions.organization_id", "document_revisions.project_id",
                "document_revisions.document_id", "document_revisions.id",
                "document_revisions.content_checksum_sha256",
            ],
            name="fk_storage_binding_revision_content", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_binding_intent_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "storage_candidate_id", "content_sha256", "byte_length"],
            [
                "document_storage_candidates.organization_id", "document_storage_candidates.id",
                "document_storage_candidates.content_sha256", "document_storage_candidates.byte_length",
            ],
            name="fk_storage_binding_candidate_integrity", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("provider_kind IN ('fake')", name="chk_storage_binding_provider"),
        sa.CheckConstraint("checksum_algorithm = 'SHA256'", name="chk_storage_binding_checksum_algorithm"),
        sa.CheckConstraint("byte_length >= 0", name="chk_storage_binding_size"),
        sa.CheckConstraint("minimum_retain_until >= retention_anchor_at", name="chk_storage_binding_retention"),
        sa.CheckConstraint(_sha256_check("content_sha256"), name="chk_storage_binding_content"),
    )


def downgrade() -> None:
    op.drop_table("storage_object_bindings")
    op.drop_table("document_storage_execution_states")
    op.drop_table("document_storage_execution_events")
    op.drop_table("document_storage_candidates")
    op.drop_index("idx_storage_intent_document", table_name="document_storage_execution_intents")
    op.drop_table("document_storage_execution_intents")
    op.drop_constraint("uq_document_revision_content_checksum", "document_revisions", type_="unique")
