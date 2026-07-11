"""create_evidence_core_tables

Revision ID: a87a9b6da999
Revises: a87a9b6da998
Create Date: 2026-07-07 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a87a9b6da999'
down_revision = 'a87a9b6da998'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create evidence_sources
    op.create_table(
        'evidence_sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Create evidence_files
    op.create_table(
        'evidence_files',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=128), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('object_key', sa.String(length=512), nullable=False),
        sa.Column('checksum', sa.String(length=255), nullable=False),
        sa.Column('sensitivity_level', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('uploaded_by', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], name='fk_evidence_files_uploader', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create evidence_links
    op.create_table(
        'evidence_links',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('evidence_file_id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(length=128), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_by', sa.UUID(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delete_reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['evidence_file_id'], ['evidence_files.id'], name='fk_evidence_links_file', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], name='fk_evidence_links_deleter', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_evidence_links_creator', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evidence_link_target', 'evidence_links', ['target_type', 'target_id'])

    # 4. Create evidence_access_logs
    op.create_table(
        'evidence_access_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('evidence_file_id', sa.UUID(), nullable=False),
        sa.Column('accessed_by', sa.UUID(), nullable=False),
        sa.Column('access_type', sa.String(length=50), nullable=False),
        sa.Column('access_reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['evidence_file_id'], ['evidence_files.id'], name='fk_evidence_access_logs_file', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['accessed_by'], ['users.id'], name='fk_evidence_access_logs_accessor', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('evidence_access_logs')
    op.drop_index('idx_evidence_link_target', table_name='evidence_links')
    op.drop_table('evidence_links')
    op.drop_table('evidence_files')
    op.drop_table('evidence_sources')
