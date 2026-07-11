"""create_document_engine_tables

Revision ID: a87a9b6da9a2
Revises: a87a9b6da9a1
Create Date: 2026-07-08 21:40:00.000000

"""

from typing import Sequence, Optional, Union
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a87a9b6da9a2"
down_revision: Optional[str] = "a87a9b6da9a1"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    # 1. document_templates
    op.create_table(
        "document_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("replacement_template_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["replacement_template_id"], ["document_templates.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("code"),
    )

    # 2. template_versions
    op.create_table(
        "template_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_template_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_file_id", sa.UUID(), nullable=True),
        sa.Column("template_format", sa.String(length=50), nullable=False),
        sa.Column("placeholder_manifest", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column("replacement_version_id", sa.UUID(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_template_id"], ["document_templates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["source_file_id"], ["evidence_files.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["replacement_version_id"], ["template_versions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "document_template_id", "version_number", name="uq_template_version_no"
        ),
    )

    # 3. computed_placeholder_expressions
    op.create_table(
        "computed_placeholder_expressions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("placeholder_key", sa.String(length=255), nullable=False),
        sa.Column("expression_type", sa.String(length=50), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("output_data_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )

    # 4. template_placeholders
    op.create_table(
        "template_placeholders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("template_version_id", sa.UUID(), nullable=False),
        sa.Column("placeholder_key", sa.String(length=255), nullable=False),
        sa.Column("label_vi", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=50), nullable=False),
        sa.Column("source_context", sa.String(length=50), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("default_value", sa.JSON(), nullable=True),
        sa.Column("format_rule", sa.JSON(), nullable=True),
        sa.Column("validation_rule", sa.JSON(), nullable=True),
        sa.Column("computed_expression_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_version_id"], ["template_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["computed_expression_id"], ["computed_placeholder_expressions.id"], ondelete="SET NULL"
        ),
    )

    # 5. placeholder_bindings
    op.create_table(
        "placeholder_bindings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("template_version_id", sa.UUID(), nullable=False),
        sa.Column("template_placeholder_id", sa.UUID(), nullable=False),
        sa.Column("binding_path", sa.String(length=255), nullable=False),
        sa.Column("binding_type", sa.String(length=50), nullable=False),
        sa.Column("fallback_value", sa.JSON(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_version_id"], ["template_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["template_placeholder_id"], ["template_placeholders.id"], ondelete="RESTRICT"
        ),
    )

    # 6. render_jobs
    op.create_table(
        "render_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("template_version_id", sa.UUID(), nullable=False),
        sa.Column("render_mode", sa.String(length=50), nullable=False),
        sa.Column("output_formats", sa.JSON(), nullable=False),
        sa.Column("data_snapshot", sa.JSON(), nullable=False),
        sa.Column("data_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("failed_step", sa.String(length=100), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("timeout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_version_id"], ["template_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )

    # 7. generated_documents
    op.create_table(
        "generated_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("render_job_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("output_format", sa.String(length=10), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("template_version_id", sa.UUID(), nullable=False),
        sa.Column("data_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("archived_by", sa.UUID(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["render_job_id"], ["render_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_version_id"], ["template_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], ondelete="RESTRICT"),
    )

    # 8. document_packages
    op.create_table(
        "document_packages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("package_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )

    # 9. document_package_items
    op.create_table(
        "document_package_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_package_id", sa.UUID(), nullable=False),
        sa.Column("generated_document_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_package_id"], ["document_packages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["generated_document_id"], ["generated_documents.id"], ondelete="RESTRICT"
        ),
    )


def downgrade() -> None:
    op.drop_table("document_package_items")
    op.drop_table("document_packages")
    op.drop_table("generated_documents")
    op.drop_table("render_jobs")
    op.drop_table("placeholder_bindings")
    op.drop_table("template_placeholders")
    op.drop_table("computed_placeholder_expressions")
    op.drop_table("template_versions")
    op.drop_table("document_templates")
