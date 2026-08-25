"""S15-PR-004 create dossier paired alignments table

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-08-25 23:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dossier_paired_alignments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('dossier_bundle_id', sa.Uuid(), nullable=False),
        sa.Column('alignment_status', sa.String(length=50), nullable=False),  # aligned, unaligned, needs_human_review
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('tech_rows_matched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quote_observations_matched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('differences_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['dossier_bundle_id'], ['dossier_bundles.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'dossier_bundle_id', name='uq_dossier_paired_alignment_bundle')
    )
    op.create_index('idx_paired_align_bundle', 'dossier_paired_alignments', ['dossier_bundle_id'])


def downgrade() -> None:
    op.drop_table('dossier_paired_alignments')
