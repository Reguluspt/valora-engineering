"""S14-PR-001 create raw asset observations and contextual asset aliases

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-08-25 22:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'raw_asset_observations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=True),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('import_batch_id', sa.Uuid(), nullable=False),
        sa.Column('source_artifact_id', sa.Uuid(), nullable=False),
        sa.Column('structure_snapshot_id', sa.Uuid(), nullable=False),
        sa.Column('staging_row_id', sa.Uuid(), nullable=True),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('sheet_name', sa.String(length=255), nullable=False),
        sa.Column('raw_asset_name', sa.Text(), nullable=False),
        sa.Column('raw_unit', sa.String(length=100), nullable=True),
        sa.Column('raw_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('raw_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('evidence_note', sa.Text(), nullable=True),
        sa.Column('section_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['import_batch_id'], ['project_asset_import_batches.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['source_artifact_id'], ['import_source_artifacts.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['structure_snapshot_id'], ['workbook_structure_snapshots.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['staging_row_id'], ['project_asset_import_staging_rows.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_raw_obs_org', 'raw_asset_observations', ['organization_id'])
    op.create_index('idx_raw_obs_customer', 'raw_asset_observations', ['customer_id'])
    op.create_index('idx_raw_obs_batch', 'raw_asset_observations', ['import_batch_id'])
    op.create_index('idx_raw_obs_artifact', 'raw_asset_observations', ['source_artifact_id'])

    op.create_table(
        'contextual_asset_aliases',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=True),
        sa.Column('alias_name', sa.Text(), nullable=False),
        sa.Column('normalized_alias_name', sa.Text(), nullable=False),
        sa.Column('canonical_asset_id', sa.Uuid(), nullable=True),
        sa.Column('asset_variant_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('source_decision_id', sa.Uuid(), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ctx_alias_org', 'contextual_asset_aliases', ['organization_id'])
    op.create_index('idx_ctx_alias_customer', 'contextual_asset_aliases', ['customer_id'])
    op.create_index('idx_ctx_alias_normalized', 'contextual_asset_aliases', ['organization_id', 'customer_id', 'normalized_alias_name'])


def downgrade() -> None:
    op.drop_table('contextual_asset_aliases')
    op.drop_table('raw_asset_observations')
