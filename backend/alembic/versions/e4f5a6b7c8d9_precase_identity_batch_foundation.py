"""Pre-case nullable Customer snapshots and explicit current batch foundation.

Revision ID: e4f5a6b7c8d9
Revises: c9d0e1f2a3b4
"""

import hashlib
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FACT_TABLES = (
    "column_mapping_decisions",
    "column_mapping_profile_usages",
    "raw_asset_observations",
    "preliminary_analysis_snapshots",
    "preliminary_result_artifacts",
)
DECISION_LINEAGE = (
    "organization_id", "project_id", "import_batch_id",
    "source_artifact_id", "structure_snapshot_id",
)


def _refuse_if_rows(query: str, reason: str) -> None:
    if op.get_bind().execute(sa.text(f"SELECT EXISTS ({query})")).scalar_one():
        raise RuntimeError(f"G1.1A migration refused: {reason}")


def _fk(name: str, source: str, target: str, local: tuple[str, ...], remote: tuple[str, ...]) -> None:
    op.create_foreign_key(name, source, target, local, remote, ondelete="RESTRICT")


def _preflight_upgrade() -> None:
    _refuse_if_rows(
        "SELECT 1 FROM projects p LEFT JOIN customers c "
        "ON c.organization_id = p.organization_id AND c.id = p.customer_id "
        "WHERE c.id IS NULL",
        "existing Project has an orphan or cross-tenant Customer",
    )
    for table in FACT_TABLES:
        _refuse_if_rows(
            f"SELECT 1 FROM {table} f LEFT JOIN projects p "
            "ON p.organization_id = f.organization_id AND p.id = f.project_id "
            "LEFT JOIN customers c ON c.organization_id = f.organization_id "
            "AND c.id = f.customer_id "
            "WHERE p.id IS NULL OR c.id IS NULL OR p.customer_id <> f.customer_id",
            f"{table} has orphan, cross-tenant or contradictory Customer lineage",
        )
    _refuse_if_rows(
        "SELECT 1 FROM project_asset_import_batches b LEFT JOIN projects p "
        "ON p.organization_id = b.organization_id AND p.id = b.project_id "
        "WHERE p.id IS NULL",
        "import batch has orphan or cross-tenant Project",
    )
    _refuse_if_rows(
        "SELECT 1 FROM project_asset_import_batches b "
        "LEFT JOIN import_source_artifacts s ON s.import_batch_id = b.id "
        "AND s.id = b.current_source_artifact_id "
        "AND s.organization_id = b.organization_id AND s.project_id = b.project_id "
        "WHERE b.current_source_artifact_id IS NOT NULL AND s.id IS NULL",
        "import batch points to a foreign source generation",
    )
    _refuse_if_rows(
        "SELECT 1 FROM projects p JOIN project_asset_import_batches b "
        "ON b.organization_id = p.organization_id AND b.project_id = p.id "
        "JOIN preliminary_result_artifacts r "
        "ON r.organization_id = p.organization_id AND r.project_id = p.id "
        "WHERE (SELECT count(*) FROM project_asset_import_batches x "
        "WHERE x.organization_id = p.organization_id AND x.project_id = p.id) = 1 "
        "AND r.lineage_manifest->>'import_batch_id' IS NOT NULL "
        "AND r.lineage_manifest->>'import_batch_id' <> b.id::text",
        "sole batch contradicts immutable result lineage",
    )


def _backfill_pointer() -> None:
    # A sole valid batch is unambiguous; preflight and existing FKs validate its lineage.
    op.execute(sa.text(
        "UPDATE projects p SET current_preliminary_import_batch_id = b.id "
        "FROM project_asset_import_batches b "
        "WHERE b.organization_id = p.organization_id AND b.project_id = p.id "
        "AND (SELECT count(*) FROM project_asset_import_batches x "
        "WHERE x.organization_id = p.organization_id AND x.project_id = p.id) = 1"
    ))
    # A committed immutable chain is the only migration authority among multiple batches.
    # Every equality below is an accepted persisted identity, version or digest claim.
    op.execute(sa.text(
        "WITH proven AS ("
        " SELECT p.organization_id, p.id AS project_id, a.import_batch_id "
        " FROM projects p "
        " JOIN project_official_intake_commits c ON c.organization_id = p.organization_id "
        " AND c.project_id = p.id AND c.customer_id = p.customer_id "
        " JOIN preliminary_result_artifacts r ON r.organization_id = c.organization_id "
        " AND r.project_id = c.project_id AND r.id = c.preliminary_result_artifact_id "
        " AND r.version = c.preliminary_result_version "
        " AND r.content_checksum_sha256 = c.preliminary_result_sha256 "
        " AND r.source_snapshot_sha256 = c.source_snapshot_sha256 "
        " JOIN preliminary_analysis_snapshots a ON a.organization_id = r.organization_id "
        " AND a.project_id = r.project_id "
        " AND a.id::text = r.lineage_manifest #>> '{analysis_snapshot,id}' "
        " AND a.version::text = r.lineage_manifest #>> '{analysis_snapshot,version}' "
        " AND a.line_manifest_digest_sha256 = "
        "     r.lineage_manifest #>> '{analysis_snapshot,line_manifest_digest_sha256}' "
        " JOIN project_asset_import_batches b ON b.organization_id = a.organization_id "
        " AND b.project_id = a.project_id AND b.id = a.import_batch_id "
        " WHERE r.lineage_manifest->>'import_batch_id' = a.import_batch_id::text "
        " AND r.source_snapshot_sha256 = "
        "     r.lineage_manifest #>> '{analysis_snapshot,canonical_digest_sha256}' "
        " AND (SELECT count(*) FROM project_asset_import_batches x "
        "      WHERE x.organization_id = p.organization_id AND x.project_id = p.id) > 1"
        "), unique_proven AS ("
        " SELECT p.organization_id, p.project_id, p.import_batch_id AS batch_id "
        " FROM proven p WHERE (SELECT count(*) FROM proven q "
        " WHERE q.organization_id = p.organization_id AND q.project_id = p.project_id) = 1"
        ") UPDATE projects p SET current_preliminary_import_batch_id = u.batch_id "
        " FROM unique_proven u WHERE p.organization_id = u.organization_id "
        " AND p.id = u.project_id"
    ))
    # Recompute the immutable analysis digests; a manifest's own claim is not proof.
    candidates = op.get_bind().execute(sa.text(
        "SELECT p.id AS project_id, p.organization_id, a.id AS snapshot_id, "
        "a.import_batch_id, a.version, a.line_manifest, "
        "a.line_manifest_digest_sha256, a.mapping_decision_id, "
        "a.mapping_profile_usage_id, a.mapping_decision_digest_sha256, "
        "a.profile_usage_mapping_digest_sha256, a.source_artifact_generation, "
        "a.source_artifact_id, a.structure_snapshot_id, r.source_snapshot_sha256, "
        "d.mapping_digest_sha256 AS decision_digest, "
        "u.mapping_digest_sha256 AS usage_digest, s.generation AS source_generation "
        "FROM projects p JOIN project_official_intake_commits c "
        "ON c.organization_id = p.organization_id AND c.project_id = p.id "
        "JOIN preliminary_result_artifacts r ON r.id = c.preliminary_result_artifact_id "
        "JOIN preliminary_analysis_snapshots a ON a.id::text = "
        "r.lineage_manifest #>> '{analysis_snapshot,id}' "
        "JOIN column_mapping_decisions d ON d.id = a.mapping_decision_id "
        "JOIN column_mapping_profile_usages u ON u.id = a.mapping_profile_usage_id "
        "JOIN import_source_artifacts s ON s.id = a.source_artifact_id "
        "WHERE p.current_preliminary_import_batch_id = a.import_batch_id "
        "AND (SELECT count(*) FROM project_asset_import_batches b "
        "WHERE b.organization_id = p.organization_id AND b.project_id = p.id) > 1"
    )).mappings().all()
    for row in candidates:
        line_digest = hashlib.sha256(json.dumps(
            row["line_manifest"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        payload = {
            "contract": "preliminary-analysis-canonical-digest-v1",
            "import_batch_id": str(row["import_batch_id"]),
            "line_manifest_digest_sha256": row["line_manifest_digest_sha256"],
            "mapping_decision_digest_sha256": row["mapping_decision_digest_sha256"],
            "mapping_decision_id": str(row["mapping_decision_id"]),
            "mapping_profile_usage_id": str(row["mapping_profile_usage_id"]),
            "organization_id": str(row["organization_id"]),
            "profile_usage_mapping_digest_sha256": row["profile_usage_mapping_digest_sha256"],
            "project_id": str(row["project_id"]),
            "snapshot_id": str(row["snapshot_id"]),
            "source_artifact_generation": row["source_artifact_generation"],
            "source_artifact_id": str(row["source_artifact_id"]),
            "structure_snapshot_id": str(row["structure_snapshot_id"]),
            "version": row["version"],
        }
        snapshot_digest = hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        if (
            line_digest != row["line_manifest_digest_sha256"]
            or snapshot_digest != row["source_snapshot_sha256"]
            or row["mapping_decision_digest_sha256"] != row["decision_digest"]
            or row["profile_usage_mapping_digest_sha256"] != row["usage_digest"]
            or row["source_artifact_generation"] != row["source_generation"]
        ):
            op.get_bind().execute(sa.text(
                "UPDATE projects SET current_preliminary_import_batch_id = NULL "
                "WHERE organization_id = :org AND id = :project"
            ), {"org": row["organization_id"], "project": row["project_id"]})


def upgrade() -> None:
    _preflight_upgrade()
    op.create_unique_constraint(
        "uq_mapping_decision_lineage_id_without_customer", "column_mapping_decisions",
        [*DECISION_LINEAGE, "id"],
    )
    op.create_unique_constraint(
        "uq_preliminary_result_tenant_project_id_without_customer",
        "preliminary_result_artifacts", ["organization_id", "project_id", "id"],
    )
    op.add_column("projects", sa.Column("current_preliminary_import_batch_id", sa.Uuid(), nullable=True))
    _backfill_pointer()

    _fk("fk_project_customer_tenant", "projects", "customers",
        ("organization_id", "customer_id"), ("organization_id", "id"))
    _fk("fk_project_current_preliminary_batch_tenant", "projects", "project_asset_import_batches",
        ("organization_id", "id", "current_preliminary_import_batch_id"),
        ("organization_id", "project_id", "id"))
    op.create_index("idx_project_current_preliminary_batch", "projects", ["current_preliminary_import_batch_id"])

    project_sources = (
        ("column_mapping_decisions", "fk_mapping_decision_project_tenant"),
        ("column_mapping_profile_usages", "fk_mapping_usage_project_tenant"),
        ("raw_asset_observations", "fk_raw_obs_project_tenant"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_project_without_customer"),
        ("preliminary_result_artifacts", "fk_preliminary_result_project_without_customer"),
    )
    for table, name in project_sources:
        _fk(name, table, "projects", ("organization_id", "project_id"), ("organization_id", "id"))
    for table, name in (
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_customer_tenant"),
        ("preliminary_result_artifacts", "fk_preliminary_result_customer_tenant"),
    ):
        _fk(name, table, "customers", ("organization_id", "customer_id"), ("organization_id", "id"))

    for name, table, column in (
        ("fk_mapping_decision_proposal_without_customer", "column_mapping_decisions", "proposal_decision_id"),
        ("fk_mapping_usage_confirmation_without_customer", "column_mapping_profile_usages", "confirmation_decision_id"),
        ("fk_preliminary_analysis_decision_without_customer", "preliminary_analysis_snapshots", "mapping_decision_id"),
    ):
        _fk(name, table, "column_mapping_decisions", (*DECISION_LINEAGE, column), (*DECISION_LINEAGE, "id"))
    _fk("fk_official_intake_artifact_without_customer", "project_official_intake_commits",
        "preliminary_result_artifacts",
        ("organization_id", "project_id", "preliminary_result_artifact_id"),
        ("organization_id", "project_id", "id"))

    # New FKs above have validated all old rows before any old ownership path is removed.
    for table, name in (
        ("column_mapping_decisions", "fk_mapping_decision_proposal_lineage"),
        ("column_mapping_profile_usages", "fk_mapping_usage_confirmation_lineage"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_decision_tenant"),
        ("project_official_intake_commits", "fk_official_intake_artifact_tenant"),
        ("column_mapping_decisions", "fk_mapping_decision_project_customer_tenant"),
        ("column_mapping_profile_usages", "fk_mapping_usage_project_customer_tenant"),
        ("raw_asset_observations", "fk_raw_obs_project_customer_tenant"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_project_tenant"),
        ("preliminary_result_artifacts", "fk_preliminary_result_project_tenant"),
    ):
        op.drop_constraint(name, table, type_="foreignkey")
    op.drop_constraint("uq_mapping_decision_tenant_lineage_id", "column_mapping_decisions", type_="unique")
    op.drop_constraint("uq_preliminary_result_tenant_project_id", "preliminary_result_artifacts", type_="unique")
    op.drop_constraint("projects_customer_id_fkey", "projects", type_="foreignkey")
    for table in ("projects", *FACT_TABLES):
        op.alter_column(table, "customer_id", existing_type=sa.Uuid(), nullable=True)


def _preflight_downgrade() -> None:
    for table in ("projects", *FACT_TABLES):
        _refuse_if_rows(f"SELECT 1 FROM {table} WHERE customer_id IS NULL",
                        f"{table} has unbound Customer history")
    _refuse_if_rows(
        "SELECT 1 FROM projects p WHERE "
        "(SELECT count(*) FROM project_asset_import_batches b WHERE b.organization_id = p.organization_id "
        "AND b.project_id = p.id) > 1 OR "
        "(SELECT count(*) FROM project_asset_import_batches b WHERE b.organization_id = p.organization_id "
        "AND b.project_id = p.id) = 1 AND (p.current_preliminary_import_batch_id IS NULL "
        "OR NOT EXISTS (SELECT 1 FROM project_asset_import_batches b "
        "WHERE b.organization_id = p.organization_id AND b.project_id = p.id "
        "AND b.id = p.current_preliminary_import_batch_id)) OR "
        "(SELECT count(*) FROM project_asset_import_batches b WHERE b.organization_id = p.organization_id "
        "AND b.project_id = p.id) = 0 AND p.current_preliminary_import_batch_id IS NOT NULL",
        "current batch or multi-batch state is not representable by v1",
    )
    for table in ("preliminary_analysis_snapshots", "preliminary_result_artifacts"):
        _refuse_if_rows(
            f"SELECT 1 FROM {table} GROUP BY organization_id, project_id HAVING "
            "count(*) > 1 OR max(version) > 1",
            f"{table} has versioned state beyond v1",
        )
    for table in FACT_TABLES:
        _refuse_if_rows(
            f"SELECT 1 FROM {table} f JOIN projects p ON "
            "p.organization_id = f.organization_id AND p.id = f.project_id "
            "WHERE f.customer_id <> p.customer_id",
            f"{table} Customer snapshot differs from v1 Project binding",
        )
    _refuse_if_rows(
        "SELECT 1 FROM project_official_intake_commits c "
        "JOIN preliminary_result_artifacts r ON r.id = c.preliminary_result_artifact_id "
        "WHERE c.customer_id <> r.customer_id",
        "Official Intake artifact Customer differs from v1 binding",
    )


def downgrade() -> None:
    _preflight_downgrade()
    for table in ("projects", *FACT_TABLES):
        op.alter_column(table, "customer_id", existing_type=sa.Uuid(), nullable=False)
    op.create_unique_constraint(
        "uq_mapping_decision_tenant_lineage_id", "column_mapping_decisions",
        ["organization_id", "customer_id", *DECISION_LINEAGE[1:], "id"],
    )
    op.create_unique_constraint(
        "uq_preliminary_result_tenant_project_id", "preliminary_result_artifacts",
        ["organization_id", "customer_id", "project_id", "id"],
    )
    for table, name in (
        ("column_mapping_decisions", "fk_mapping_decision_project_customer_tenant"),
        ("column_mapping_profile_usages", "fk_mapping_usage_project_customer_tenant"),
        ("raw_asset_observations", "fk_raw_obs_project_customer_tenant"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_project_tenant"),
        ("preliminary_result_artifacts", "fk_preliminary_result_project_tenant"),
    ):
        _fk(name, table, "projects", ("organization_id", "customer_id", "project_id"),
            ("organization_id", "customer_id", "id"))
    customer_lineage = ("organization_id", "customer_id", *DECISION_LINEAGE[1:])
    for table, name, column in (
        ("column_mapping_decisions", "fk_mapping_decision_proposal_lineage", "proposal_decision_id"),
        ("column_mapping_profile_usages", "fk_mapping_usage_confirmation_lineage", "confirmation_decision_id"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_decision_tenant", "mapping_decision_id"),
    ):
        _fk(name, table, "column_mapping_decisions", (*customer_lineage, column),
            (*customer_lineage, "id"))
    _fk("fk_official_intake_artifact_tenant", "project_official_intake_commits",
        "preliminary_result_artifacts",
        ("organization_id", "customer_id", "project_id", "preliminary_result_artifact_id"),
        ("organization_id", "customer_id", "project_id", "id"))
    _fk("projects_customer_id_fkey", "projects", "customers", ("customer_id",), ("id",))

    for table, name in (
        ("column_mapping_decisions", "fk_mapping_decision_proposal_without_customer"),
        ("column_mapping_profile_usages", "fk_mapping_usage_confirmation_without_customer"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_decision_without_customer"),
        ("project_official_intake_commits", "fk_official_intake_artifact_without_customer"),
        ("column_mapping_decisions", "fk_mapping_decision_project_tenant"),
        ("column_mapping_profile_usages", "fk_mapping_usage_project_tenant"),
        ("raw_asset_observations", "fk_raw_obs_project_tenant"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_project_without_customer"),
        ("preliminary_result_artifacts", "fk_preliminary_result_project_without_customer"),
        ("preliminary_analysis_snapshots", "fk_preliminary_analysis_customer_tenant"),
        ("preliminary_result_artifacts", "fk_preliminary_result_customer_tenant"),
        ("projects", "fk_project_current_preliminary_batch_tenant"),
        ("projects", "fk_project_customer_tenant"),
    ):
        op.drop_constraint(name, table, type_="foreignkey")
    op.drop_index("idx_project_current_preliminary_batch", table_name="projects")
    op.drop_column("projects", "current_preliminary_import_batch_id")
    op.drop_constraint("uq_mapping_decision_lineage_id_without_customer", "column_mapping_decisions", type_="unique")
    op.drop_constraint("uq_preliminary_result_tenant_project_id_without_customer", "preliminary_result_artifacts", type_="unique")
