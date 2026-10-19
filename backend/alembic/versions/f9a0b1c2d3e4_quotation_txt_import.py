"""Immutable human TXT import custody, Issue 208."""
from alembic import op
import sqlalchemy as sa

revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None
TABLES = ("quotation_document_import_requests", "quotation_document_import_receipts")


def upgrade():
    op.create_table('quotation_document_import_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=False),
    sa.Column('command_id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('execution_intent_id', sa.Uuid(), nullable=False),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('media_type', sa.String(length=64), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=False),
    sa.Column('byte_length', sa.BigInteger(), nullable=False),
    sa.Column('expected_case_version', sa.String(length=64), nullable=False),
    sa.Column('expected_project_row_version', sa.Integer(), nullable=False),
    sa.Column('snapshot_sha256', sa.String(length=64), nullable=False),
    sa.Column('plan_sha256', sa.String(length=64), nullable=False),
    sa.Column('decision_sha256', sa.String(length=64), nullable=False),
    sa.Column('request_sha256', sa.String(length=64), nullable=False),
    sa.Column('retention_policy_code', sa.String(length=64), nullable=False),
    sa.Column('policy_version', sa.Integer(), nullable=False),
    sa.Column('policy_manifest_sha256', sa.String(length=64), nullable=False),
    sa.Column('policy_manifest', sa.JSON(), nullable=False),
    sa.Column('storage_profile_id', sa.String(length=64), nullable=False),
    sa.Column('provider_kind', sa.String(length=32), nullable=False),
    sa.Column('container_name', sa.String(length=255), nullable=False),
    sa.Column('prepared_audit_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("length(content_sha256) = 64 AND content_sha256 = lower(content_sha256) AND content_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_request_content_sha256'),
    sa.CheckConstraint("length(decision_sha256) = 64 AND decision_sha256 = lower(decision_sha256) AND decision_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_request_decision_sha256'),
    sa.CheckConstraint("length(expected_case_version) = 64 AND expected_case_version = lower(expected_case_version) AND expected_case_version ~ '^[0-9a-f]{64}$'", name='chk_txt_request_expected_case_version'),
    sa.CheckConstraint("length(plan_sha256) = 64 AND plan_sha256 = lower(plan_sha256) AND plan_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_request_plan_sha256'),
    sa.CheckConstraint("length(policy_manifest_sha256) = 64 AND policy_manifest_sha256 = lower(policy_manifest_sha256) AND policy_manifest_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_request_policy_manifest_sha256'),
    sa.CheckConstraint("length(request_sha256) = 64 AND request_sha256 = lower(request_sha256) AND request_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_request_request_sha256'),
    sa.CheckConstraint("length(snapshot_sha256) = 64 AND snapshot_sha256 = lower(snapshot_sha256) AND snapshot_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_request_snapshot_sha256'),
    sa.CheckConstraint("policy_version = 1 AND retention_policy_code = 'quotation-txt-record-10y-v1'", name='chk_txt_request_policy'),
    sa.CheckConstraint("provider_kind = 'local' AND storage_profile_id = 'exchange-local' AND container_name = 'valora-document-blobs'", name='chk_txt_request_target'),
    sa.CheckConstraint('byte_length BETWEEN 1 AND 1048576 AND expected_project_row_version > 0', name='chk_txt_request_bounds'),
    sa.ForeignKeyConstraint(['organization_id', 'actor_user_id'], ['users.organization_id', 'users.id'], name='fk_txt_request_actor', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'execution_intent_id'], ['document_storage_execution_intents.organization_id', 'document_storage_execution_intents.id'], name='fk_txt_request_intent', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'document_id'], ['document_records.organization_id', 'document_records.project_id', 'document_records.id'], name='fk_txt_request_document', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id'], ['projects.organization_id', 'projects.id'], name='fk_txt_request_project', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['prepared_audit_id'], ['audit_events.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('command_id', name='uq_txt_import_command'),
    sa.UniqueConstraint('execution_intent_id', name='uq_txt_import_intent'),
    sa.UniqueConstraint('organization_id', 'project_id', 'actor_user_id', 'id', name='uq_txt_import_request_scope'),
    sa.UniqueConstraint('prepared_audit_id', name='uq_txt_import_prepared_audit')
    )
    op.create_table('quotation_document_import_receipts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=False),
    sa.Column('request_id', sa.Uuid(), nullable=False),
    sa.Column('execution_intent_id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('revision_id', sa.Uuid(), nullable=False),
    sa.Column('binding_id', sa.Uuid(), nullable=False),
    sa.Column('milestone_audit_id', sa.Uuid(), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=False),
    sa.Column('byte_length', sa.BigInteger(), nullable=False),
    sa.Column('retention_policy_code', sa.String(length=64), nullable=False),
    sa.Column('policy_version', sa.Integer(), nullable=False),
    sa.Column('policy_manifest_sha256', sa.String(length=64), nullable=False),
    sa.Column('policy_manifest', sa.JSON(), nullable=False),
    sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('retention_anchor_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('minimum_retain_until', sa.DateTime(timezone=True), nullable=False),
    sa.Column('post_project_row_version', sa.Integer(), nullable=False),
    sa.Column('snapshot', sa.JSON(), nullable=False),
    sa.Column('receipt_sha256', sa.String(length=64), nullable=False),
    sa.CheckConstraint("length(content_sha256) = 64 AND content_sha256 = lower(content_sha256) AND content_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_receipt_content_sha256'),
    sa.CheckConstraint("length(policy_manifest_sha256) = 64 AND policy_manifest_sha256 = lower(policy_manifest_sha256) AND policy_manifest_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_receipt_policy_manifest_sha256'),
    sa.CheckConstraint("length(receipt_sha256) = 64 AND receipt_sha256 = lower(receipt_sha256) AND receipt_sha256 ~ '^[0-9a-f]{64}$'", name='chk_txt_receipt_receipt_sha256'),
    sa.CheckConstraint("policy_version = 1 AND retention_policy_code = 'quotation-txt-record-10y-v1'", name='chk_txt_receipt_policy'),
    sa.CheckConstraint('byte_length BETWEEN 1 AND 1048576 AND post_project_row_version > 1', name='chk_txt_receipt_bounds'),
    sa.CheckConstraint('finalized_at = retention_anchor_at AND minimum_retain_until >= retention_anchor_at', name='chk_txt_receipt_retention'),
    sa.ForeignKeyConstraint(['binding_id'], ['storage_object_bindings.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['milestone_audit_id'], ['audit_events.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'execution_intent_id'], ['storage_object_bindings.organization_id', 'storage_object_bindings.execution_intent_id'], name='fk_txt_receipt_binding_tenant', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'actor_user_id', 'request_id'], ['quotation_document_import_requests.organization_id', 'quotation_document_import_requests.project_id', 'quotation_document_import_requests.actor_user_id', 'quotation_document_import_requests.id'], name='fk_txt_receipt_request', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'document_id', 'revision_id', 'content_sha256'], ['document_revisions.organization_id', 'document_revisions.project_id', 'document_revisions.document_id', 'document_revisions.id', 'document_revisions.content_checksum_sha256'], name='fk_txt_receipt_revision', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('binding_id', name='uq_txt_receipt_binding'),
    sa.UniqueConstraint('execution_intent_id', name='uq_txt_receipt_intent'),
    sa.UniqueConstraint('milestone_audit_id', name='uq_txt_receipt_audit'),
    sa.UniqueConstraint('request_id', name='uq_txt_receipt_request'),
    sa.UniqueConstraint('revision_id', name='uq_txt_receipt_revision')
    )
    if op.get_context().dialect.name == "postgresql":
        op.create_check_constraint("chk_txt_receipt_calendar_floor", TABLES[1],
            "minimum_retain_until = ((retention_anchor_at AT TIME ZONE 'UTC') + interval '10 years') AT TIME ZONE 'UTC'")
        op.execute("""CREATE FUNCTION quotation_txt_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'Quotation TXT custody is immutable'; END; $$""")
        for table in TABLES:
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION quotation_txt_append_only()")
        op.execute("""CREATE FUNCTION quotation_txt_source_pin() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE pinned boolean; source_id uuid; BEGIN
            IF TG_TABLE_NAME = 'audit_events' THEN
                IF OLD.event_name IN ('QUOTATION_DOCUMENT_IMPORTED', 'QUOTATION_DOCUMENT_IMPORT_PREPARED') THEN
                    RAISE EXCEPTION 'Quotation TXT custody audit is immutable';
                END IF;
            ELSE
                source_id := CASE WHEN TG_TABLE_NAME = 'document_revisions' THEN OLD.id
                    ELSE (to_jsonb(OLD)->>'document_revision_id')::uuid END;
                EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.quotation_document_import_receipts WHERE organization_id = $1 AND revision_id = $2)', TG_TABLE_SCHEMA)
                    INTO pinned USING OLD.organization_id, source_id;
                IF pinned THEN RAISE EXCEPTION 'Original quotation TXT source is immutable'; END IF;
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW;
            END; $$""")
        for table in ("document_revisions", "storage_object_bindings", "audit_events"):
            op.execute(f"CREATE TRIGGER {table}_txt_pin BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION quotation_txt_source_pin()")
        op.execute("""CREATE FUNCTION quotation_txt_receipt_integrity() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE valid boolean; BEGIN
            SELECT EXISTS (
                SELECT 1 FROM quotation_document_import_requests q
                JOIN storage_object_bindings b ON b.id = NEW.binding_id
                JOIN audit_events a ON a.id = NEW.milestone_audit_id
                WHERE q.id = NEW.request_id
                AND (q.organization_id, q.project_id, q.actor_user_id, q.document_id, q.execution_intent_id)
                    = (NEW.organization_id, NEW.project_id, NEW.actor_user_id, NEW.document_id, NEW.execution_intent_id)
                AND (b.organization_id, b.project_id, b.document_id, b.execution_intent_id, b.document_revision_id, b.content_sha256, b.byte_length)
                    = (NEW.organization_id, NEW.project_id, NEW.document_id, NEW.execution_intent_id, NEW.revision_id, NEW.content_sha256, NEW.byte_length)
                AND b.bound_at = NEW.finalized_at AND b.retention_anchor_at = NEW.retention_anchor_at
                AND b.minimum_retain_until = NEW.minimum_retain_until AND b.retention_policy_code = NEW.retention_policy_code
                AND q.retention_policy_code = NEW.retention_policy_code AND q.policy_version = NEW.policy_version
                AND q.policy_manifest_sha256 = NEW.policy_manifest_sha256
                AND q.content_sha256 = NEW.content_sha256 AND q.byte_length = NEW.byte_length
                AND NEW.post_project_row_version = q.expected_project_row_version + 1
                AND (a.organization_id, a.actor_user_id, a.entity_id, a.event_name, a.created_at)
                    = (NEW.organization_id, NEW.actor_user_id, NEW.id, 'QUOTATION_DOCUMENT_IMPORTED', NEW.finalized_at)
            ) INTO valid;
            IF NOT valid THEN RAISE EXCEPTION 'Quotation TXT receipt integrity conflict'; END IF;
            RETURN NEW; END; $$""")
        op.execute("CREATE TRIGGER quotation_txt_receipt_integrity BEFORE INSERT ON quotation_document_import_receipts "
            "FOR EACH ROW EXECUTE FUNCTION quotation_txt_receipt_integrity()")


def downgrade():
    if op.get_context().dialect.name == "postgresql":
        for table in ("document_revisions", "storage_object_bindings", "audit_events"):
            op.execute(f"DROP TRIGGER {table}_txt_pin ON {table}")
        op.execute("DROP FUNCTION quotation_txt_source_pin()")
    for table in reversed(TABLES):
        op.drop_table(table)
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION quotation_txt_receipt_integrity()")
        op.execute("DROP FUNCTION quotation_txt_append_only()")
