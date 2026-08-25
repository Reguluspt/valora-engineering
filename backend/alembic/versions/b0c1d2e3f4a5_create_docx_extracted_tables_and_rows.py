"""S15-PR-003 create docx extracted tables and rows tables

Revision ID: b0c1d2e3f4a5
Revises: f8a9b0c1d2e3
Create Date: 2026-08-25 23:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b0c1d2e3f4a5'
down_revision: Union[str, None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'docx_extracted_tables',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('dossier_bundle_id', sa.Uuid(), nullable=False),
        sa.Column('source_file_id', sa.Uuid(), nullable=False),
        sa.Column('table_index', sa.Integer(), nullable=False),
        sa.Column('table_role_candidate', sa.String(length=50), nullable=False),  # technical_specifications, market_comparison, final_valuation_summary, unknown
        sa.Column('raw_title', sa.String(length=255), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('col_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['dossier_bundle_id'], ['dossier_bundles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['source_file_id'], ['dossier_source_files.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_docx_table_bundle', 'docx_extracted_tables', ['dossier_bundle_id'])

    op.create_table(
        'docx_extracted_rows',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('extracted_table_id', sa.Uuid(), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('cells_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['extracted_table_id'], ['docx_extracted_tables.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_docx_row_table', 'docx_extracted_rows', ['extracted_table_id'])


def downgrade() -> None:
    op.drop_table('docx_extracted_rows')
    op.drop_table('docx_extracted_tables')
