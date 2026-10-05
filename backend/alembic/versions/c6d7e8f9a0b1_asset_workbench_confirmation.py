"""Immutable Asset Workbench confirmations, withdrawals and scoped receipts.

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None
TABLES = ("asset_workbench_command_receipts", "project_asset_workbench_confirmations", "project_asset_workbench_withdrawals")


def upgrade():
    op.create_table('asset_workbench_command_receipts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('command_id', sa.Uuid(), nullable=False),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.Column('request_sha256', sa.String(length=64), nullable=False),
    sa.Column('response_metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("contract_version IN ('asset-workbench-confirmation-v1', 'asset-workbench-withdrawal-v1')", name='chk_aw_receipt_contract'),
    sa.ForeignKeyConstraint(['organization_id', 'actor_user_id'], ['users.organization_id', 'users.id'], name='fk_aw_receipt_actor', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id'], ['projects.organization_id', 'projects.id'], name='fk_aw_receipt_project', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'actor_user_id', 'session_id'], ['workbench_sessions.project_id', 'workbench_sessions.user_id', 'workbench_sessions.id'], name='fk_aw_receipt_session', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'command_id', name='uq_aw_receipt_command'),
    sa.UniqueConstraint('organization_id', 'project_id', 'actor_user_id', 'session_id', 'id', name='uq_aw_receipt_scope')
    )
    op.create_table('project_asset_workbench_confirmations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('confirmation_version', sa.Integer(), nullable=False),
    sa.Column('supersedes_confirmation_id', sa.Uuid(), nullable=True),
    sa.Column('prior_reversal_id', sa.Uuid(), nullable=True),
    sa.Column('receipt_id', sa.Uuid(), nullable=False),
    sa.Column('seal_id', sa.Uuid(), nullable=False),
    sa.Column('authoritative_set_sha256', sa.String(length=64), nullable=False),
    sa.Column('membership_version', sa.Integer(), nullable=False),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=False),
    sa.Column('content_binding', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('invocation_binding', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('pre_row_version', sa.Integer(), nullable=False),
    sa.Column('post_row_version', sa.Integer(), nullable=False),
    sa.Column('confirmed', sa.Boolean(), nullable=False),
    sa.Column('reason_note', sa.Text(), nullable=True),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("contract_version = 'asset-workbench-confirmation-v1' AND confirmation_version > 0", name='chk_aw_confirmation_contract'),
    sa.CheckConstraint('(supersedes_confirmation_id IS NULL AND reason_note IS NULL AND confirmation_version = 1 AND prior_reversal_id IS NULL) OR (supersedes_confirmation_id IS NOT NULL AND supersedes_confirmation_id != id AND reason_note IS NOT NULL AND confirmation_version > 1)', name='chk_aw_confirmation_supersession'),
    sa.CheckConstraint('membership_version = 1 AND confirmed AND pre_row_version > 0 AND post_row_version = pre_row_version + 1', name='chk_aw_confirmation_versions'),
    sa.CheckConstraint('reason_note IS NULL OR (length(trim(reason_note)) > 0 AND length(reason_note) <= 2000)', name='chk_aw_confirmation_reason'),
    sa.ForeignKeyConstraint(['organization_id', 'actor_user_id'], ['users.organization_id', 'users.id'], name='fk_aw_confirmation_actor', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'actor_user_id', 'session_id', 'receipt_id'], ['asset_workbench_command_receipts.organization_id', 'asset_workbench_command_receipts.project_id', 'asset_workbench_command_receipts.actor_user_id', 'asset_workbench_command_receipts.session_id', 'asset_workbench_command_receipts.id'], name='fk_aw_confirmation_receipt', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'seal_id'], ['project_asset_review_seals.organization_id', 'project_asset_review_seals.project_id', 'project_asset_review_seals.id'], name='fk_aw_confirmation_seal', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'supersedes_confirmation_id'], ['project_asset_workbench_confirmations.organization_id', 'project_asset_workbench_confirmations.project_id', 'project_asset_workbench_confirmations.id'], name='fk_aw_confirmation_prior', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id'], ['projects.organization_id', 'projects.id'], name='fk_aw_confirmation_project', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'actor_user_id', 'session_id'], ['workbench_sessions.project_id', 'workbench_sessions.user_id', 'workbench_sessions.id'], name='fk_aw_confirmation_session', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'project_id', 'confirmation_version', name='uq_aw_confirmation_version'),
    sa.UniqueConstraint('organization_id', 'project_id', 'id', name='uq_aw_confirmation_scope'),
    sa.UniqueConstraint('receipt_id', name='uq_aw_confirmation_receipt'),
    sa.UniqueConstraint('supersedes_confirmation_id', name='uq_aw_confirmation_successor')
    )
    op.create_table('project_asset_workbench_withdrawals',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('confirmation_id', sa.Uuid(), nullable=False),
    sa.Column('receipt_id', sa.Uuid(), nullable=False),
    sa.Column('seal_id', sa.Uuid(), nullable=False),
    sa.Column('authoritative_set_sha256', sa.String(length=64), nullable=False),
    sa.Column('membership_version', sa.Integer(), nullable=False),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=False),
    sa.Column('content_binding', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('invocation_binding', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('pre_row_version', sa.Integer(), nullable=False),
    sa.Column('post_row_version', sa.Integer(), nullable=False),
    sa.Column('confirmed', sa.Boolean(), nullable=False),
    sa.Column('reason_note', sa.Text(), nullable=True),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("contract_version = 'asset-workbench-withdrawal-v1' AND reason_note IS NOT NULL", name='chk_aw_withdrawal_contract'),
    sa.CheckConstraint('membership_version = 1 AND confirmed AND pre_row_version > 0 AND post_row_version = pre_row_version + 1', name='chk_aw_withdrawal_versions'),
    sa.CheckConstraint('reason_note IS NULL OR (length(trim(reason_note)) > 0 AND length(reason_note) <= 2000)', name='chk_aw_withdrawal_reason'),
    sa.ForeignKeyConstraint(['organization_id', 'actor_user_id'], ['users.organization_id', 'users.id'], name='fk_aw_withdrawal_actor', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'actor_user_id', 'session_id', 'receipt_id'], ['asset_workbench_command_receipts.organization_id', 'asset_workbench_command_receipts.project_id', 'asset_workbench_command_receipts.actor_user_id', 'asset_workbench_command_receipts.session_id', 'asset_workbench_command_receipts.id'], name='fk_aw_withdrawal_receipt', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'confirmation_id'], ['project_asset_workbench_confirmations.organization_id', 'project_asset_workbench_confirmations.project_id', 'project_asset_workbench_confirmations.id'], name='fk_aw_withdrawal_confirmation', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id', 'seal_id'], ['project_asset_review_seals.organization_id', 'project_asset_review_seals.project_id', 'project_asset_review_seals.id'], name='fk_aw_withdrawal_seal', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organization_id', 'project_id'], ['projects.organization_id', 'projects.id'], name='fk_aw_withdrawal_project', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'actor_user_id', 'session_id'], ['workbench_sessions.project_id', 'workbench_sessions.user_id', 'workbench_sessions.id'], name='fk_aw_withdrawal_session', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('confirmation_id', name='uq_aw_withdrawal_confirmation'),
    sa.UniqueConstraint('organization_id', 'project_id', 'id', name='uq_aw_withdrawal_scope'),
    sa.UniqueConstraint('receipt_id', name='uq_aw_withdrawal_receipt')
    )
    # ### end Alembic commands ###
    op.create_foreign_key("fk_aw_confirmation_reversal", TABLES[1], TABLES[2],
                          ["organization_id", "project_id", "prior_reversal_id"],
                          ["organization_id", "project_id", "id"], ondelete="RESTRICT")
    install_append_only()


def install_append_only():
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE FUNCTION asset_workbench_append_only() RETURNS trigger LANGUAGE plpgsql AS $$ "
                   "BEGIN RAISE EXCEPTION 'Asset Workbench evidence is append-only'; END; $$")
        for table in TABLES:
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION asset_workbench_append_only()")


def downgrade():
    op.drop_constraint("fk_aw_confirmation_reversal", TABLES[1], type_="foreignkey")
    for table in reversed(TABLES):
        op.drop_table(table)
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION asset_workbench_append_only()")
