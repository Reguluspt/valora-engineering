"""create_duplicate_merge_review_tables

Revision ID: a87a9b6da997
Revises: a87a9b6da996
Create Date: 2026-07-07 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a87a9b6da997'
down_revision = 'a87a9b6da996'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. duplicate_candidates
    op.create_table(
        'duplicate_candidates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_asset_id', sa.UUID(), nullable=False),
        sa.Column('target_asset_id', sa.UUID(), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('metadata_info', sa.JSON(), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('source_asset_id <> target_asset_id', name='chk_duplicate_diff_assets'),
        sa.ForeignKeyConstraint(['source_asset_id'], ['canonical_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_asset_id'], ['canonical_assets.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. merge_decisions
    op.create_table(
        'merge_decisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_asset_id', sa.UUID(), nullable=False),
        sa.Column('target_asset_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('configuration_flags', sa.JSON(), nullable=True),
        sa.Column('executed_by', sa.UUID(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('source_asset_id <> target_asset_id', name='chk_merge_diff_assets'),
        sa.ForeignKeyConstraint(['executed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_asset_id'], ['canonical_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_asset_id'], ['canonical_assets.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. identity_review_items
    op.create_table(
        'identity_review_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_asset_line_id', sa.UUID(), nullable=False),
        sa.Column('identity_candidate_id', sa.UUID(), nullable=True),
        sa.Column('review_status', sa.String(length=50), nullable=False),
        sa.Column('reviewer_note', sa.Text(), nullable=True),
        sa.Column('assigned_to', sa.UUID(), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['identity_candidate_id'], ['identity_candidates.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['project_asset_line_id'], ['project_asset_lines.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. identity_decision_logs
    op.create_table(
        'identity_decision_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_asset_line_id', sa.UUID(), nullable=False),
        sa.Column('decision_type', sa.String(length=50), nullable=False),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['project_asset_line_id'], ['project_asset_lines.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('identity_decision_logs')
    op.drop_table('identity_review_items')
    op.drop_table('merge_decisions')
    op.drop_table('duplicate_candidates')
