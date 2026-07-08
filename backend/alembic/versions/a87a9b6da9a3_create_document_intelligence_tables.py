"""create_document_intelligence_tables

Revision ID: a87a9b6da9a3
Revises: a87a9b6da9a2
Create Date: 2026-07-08 21:50:00.000000

"""
from typing import Sequence, Optional, Union
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a87a9b6da9a3'
down_revision: Optional[str] = 'a87a9b6da9a2'
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    # 1. parsed_documents
    op.create_table(
        'parsed_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('evidence_file_id', sa.UUID(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('text_content_hash', sa.String(length=64), nullable=True),
        sa.Column('parse_status', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['evidence_file_id'], ['evidence_files.id'], ondelete='RESTRICT')
    )

    # 2. extracted_fields
    op.create_table(
        'extracted_fields',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('parsed_document_id', sa.UUID(), nullable=False),
        sa.Column('field_key', sa.String(length=255), nullable=False),
        sa.Column('field_label', sa.String(length=255), nullable=True),
        sa.Column('extracted_value', sa.JSON(), nullable=False),
        sa.Column('normalized_value', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('source_page_number', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parsed_document_id'], ['parsed_documents.id'], ondelete='RESTRICT')
    )

    # 3. document_diffs
    op.create_table(
        'document_diffs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_document_id', sa.UUID(), nullable=False),
        sa.Column('target_document_id', sa.UUID(), nullable=False),
        sa.Column('diff_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('diff_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['source_document_id'], ['generated_documents.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_document_id'], ['parsed_documents.id'], ondelete='RESTRICT')
    )

    # 4. document_corrections
    op.create_table(
        'document_corrections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('parsed_document_id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('affects_approved_data', sa.Boolean(), nullable=False),
        sa.Column('correction_payload', sa.JSON(), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('decided_by', sa.UUID(), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parsed_document_id'], ['parsed_documents.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ondelete='RESTRICT')
    )


def downgrade() -> None:
    op.drop_table('document_corrections')
    op.drop_table('document_diffs')
    op.drop_table('extracted_fields')
    op.drop_table('parsed_documents')
