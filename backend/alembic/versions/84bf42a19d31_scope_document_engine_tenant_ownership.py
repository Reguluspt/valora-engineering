"""Scope Document Engine template codes and record expression ownership."""

import sqlalchemy as sa
from alembic import op

revision = "84bf42a19d31"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None

_GLOBAL_CODE = "document_templates_code_key"
_TENANT_CODE = "uq_document_templates_org_code"
_EXPRESSIONS = "computed_placeholder_expressions"
_OWNER_FK = "fk_computed_placeholder_expressions_template_version"
_OWNER_INDEX = "ix_computed_placeholder_expressions_template_version_id"


def upgrade() -> None:
    op.execute("LOCK TABLE document_templates IN ACCESS EXCLUSIVE MODE")
    duplicate = op.get_bind().execute(sa.text(
        "SELECT 1 FROM document_templates GROUP BY organization_id, code HAVING count(*) > 1 LIMIT 1"
    )).scalar()
    if duplicate:
        raise RuntimeError("Cannot scope template code uniqueness: duplicate organization and code pairs exist.")

    op.create_unique_constraint(_TENANT_CODE, "document_templates", ["organization_id", "code"])
    op.drop_constraint(_GLOBAL_CODE, "document_templates", type_="unique")
    op.add_column(_EXPRESSIONS, sa.Column("template_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        _OWNER_FK, _EXPRESSIONS, "template_versions", ["template_version_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index(_OWNER_INDEX, _EXPRESSIONS, ["template_version_id"])


def downgrade() -> None:
    op.execute("LOCK TABLE document_templates IN ACCESS EXCLUSIVE MODE")
    duplicate = op.get_bind().execute(sa.text(
        "SELECT 1 FROM document_templates GROUP BY code HAVING count(*) > 1 LIMIT 1"
    )).scalar()
    if duplicate:
        raise RuntimeError("Cannot restore global template code uniqueness: codes are shared by multiple organizations.")

    op.create_unique_constraint(_GLOBAL_CODE, "document_templates", ["code"])
    op.drop_constraint(_TENANT_CODE, "document_templates", type_="unique")
    op.drop_index(_OWNER_INDEX, table_name=_EXPRESSIONS)
    op.drop_constraint(_OWNER_FK, _EXPRESSIONS, type_="foreignkey")
    op.drop_column(_EXPRESSIONS, "template_version_id")
