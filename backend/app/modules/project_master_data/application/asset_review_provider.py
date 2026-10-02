"""Read-only Asset Review predicates over the shared scoped authority snapshot."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.modules.project_master_data.application.asset_review_authority import (
    AuthoritySnapshot, CONTRACT_VERSION, membership_digest,
)


PROVIDER_KEY = "asset_review_v1"
STAGE = "ASSET_REVIEW"
STALE_ORDER = ("lineage_mismatch", "selection_mismatch", "batch_state_conflict", "seal_mismatch")


@dataclass(frozen=True)
class AssetReviewProviderResult:
    result: str
    blockers: list[dict[str, Any]]
    stale: list[dict[str, Any]]
    next_action: dict[str, Any]
    provider_key: str = PROVIDER_KEY
    availability_reason: str | None = None


def _value(value) -> str:
    return str(getattr(value, "value", value))


def _context(snapshot, kind, reason, **fields):
    return {"kind": kind, "project_id": str(snapshot.project.id),
            "case_version": snapshot.case_version, "reason_code": reason, **fields}


def _action(kind, key=None, context=None, *, issue_id=None, stage=STAGE):
    return {"kind": kind, "stage": stage, "semantic_route_key": key,
            "validation_issue_id": str(issue_id) if issue_id is not None else None,
            "context": context}


def _entry(snapshot, reason, *, line=None):
    fields = {}
    if snapshot.batch is not None:
        fields["batch_id"] = str(snapshot.batch.id)
    if line is not None:
        fields["line_id"] = str(line.id)
    return _action("BLOCKER", "asset_review_entry_blocked",
                   _context(snapshot, "entry", reason, **fields))


def _membership(snapshot) -> tuple[bool | None, list]:
    """Membership remains provable independently of current source lineage."""
    seal = snapshot.seal
    if seal is None:
        return None, []
    correspondence = seal.correspondence
    if not isinstance(correspondence, list) or not correspondence:
        return None, []
    if seal.authoritative_set_sha256 != membership_digest(correspondence):
        return None, []
    try:
        pairs = [(uuid.UUID(item["line_id"]), uuid.UUID(item["staging_row_id"]),
                  item["source_row_number"]) for item in correspondence]
        line_ids = {pair[0] for pair in pairs}
        row_ids = {pair[1] for pair in pairs}
        by_id = {line.id: line for line in snapshot.lines}
        valid = (len(line_ids) == len(pairs) == len(row_ids) == len(snapshot.lines)
                 and line_ids == set(by_id)
                 and all(by_id[line_id].source_staging_row_id == row_id
                         and by_id[line_id].source_import_batch_id == seal.import_batch_id
                         for line_id, row_id, _ in pairs))
        ordered = [by_id[line_id] for line_id, _, _ in sorted(
            pairs, key=lambda item: (item[2], str(item[1]), str(item[0])),
        )] if valid else []
        return valid, ordered
    except (KeyError, TypeError, ValueError, AttributeError):
        return None, []


def _line_context(snapshot, line, reason):
    return _context(snapshot, "line", reason, membership_version=snapshot.seal.membership_version,
                    line_id=str(line.id), line_row_version=line.row_version)


def _negative_reason(line):
    review = _value(line.review_status)
    if review in ("flagged", "rejected"):
        return "review_" + review
    return "validation_invalid" if _value(line.validation_status) == "invalid" else None


def _finished(line):
    return _value(line.review_status) == "accepted" and _value(line.validation_status) == "valid"


def evaluate_asset_review_provider(
    snapshot: AuthoritySnapshot, *, effective_permissions: set[str], available: bool = True,
) -> AssetReviewProviderResult:
    """Select one deterministic action while retaining blocker and stale diagnostics."""
    if not available or snapshot.intake is None:
        reason = "provider_unwired" if not available else "official_intake_prerequisite"
        return AssetReviewProviderResult(
            "NOT_AVAILABLE", [], [], _action("UNAVAILABLE", stage=None),
            availability_reason=reason,
        )

    stale_reasons = set(snapshot.stale)
    if not snapshot.lineage_current and not stale_reasons:
        stale_reasons.add("lineage_mismatch")
    batch_status = _value(snapshot.batch.status) if snapshot.batch is not None else None
    if snapshot.batch is not None and batch_status not in (
        "parsed", "validation_failed", "ready_for_review", "applied",
    ):
        stale_reasons.add("batch_state_conflict")
    if snapshot.seal is not None and batch_status != "applied":
        stale_reasons.add("batch_state_conflict")
    if batch_status == "applied" and not snapshot.seal_current:
        stale_reasons.add("seal_mismatch")
    stale = [{"stage": STAGE, "reason_code": reason}
             for reason in STALE_ORDER if reason in stale_reasons]
    blockers = []
    actions = []

    line_ids = {line.id for line in snapshot.lines}
    for issue in sorted(snapshot.issues, key=lambda item: str(item.id)):
        target_kind = {"project": "project", "Project": "project",
                       "project_asset_line": "project_asset_line",
                       "ProjectAssetLine": "project_asset_line"}.get(issue.target_type)
        known_target = ((target_kind == "project" and issue.target_id == snapshot.project.id)
                        or (target_kind == "project_asset_line" and issue.target_id in line_ids))
        if not known_target:
            continue
        if _value(issue.status) != "open" or _value(issue.severity) != "blocking":
            continue
        context = _context(snapshot, "issue", "open_blocking_issue",
                           validation_issue_id=str(issue.id), issue_row_version=issue.row_version,
                           target_kind=target_kind, target_id=str(issue.target_id))
        actions.append(_action("BLOCKER", "asset_review_issue_blocker", context, issue_id=issue.id))
        blockers.append({"stage": STAGE, "reason_code": "open_blocking_issue",
                         "validation_issue_id": str(issue.id)})

    def entry_block(reason, *, line=None):
        actions.append(_entry(snapshot, reason, line=line))
        blockers.append({"stage": STAGE, "reason_code": reason,
                         **({"line_id": str(line.id)} if line is not None else {})})

    membership_valid, ordered_lines = _membership(snapshot)
    if snapshot.seal is not None and membership_valid is False:
        entry_block("membership_conflict")
    elif snapshot.seal is None and snapshot.lines:
        selected_row_ids = {row.id for row in snapshot.rows}
        historical_linked_apply = (batch_status == "applied"
            and all(line.source_import_batch_id == snapshot.batch.id
                    and line.source_staging_row_id in selected_row_ids for line in snapshot.lines))
        if not historical_linked_apply:
            entry_block("manual_line_conflict", line=min(snapshot.lines, key=lambda line: str(line.id)))

    manifest = getattr(snapshot.analysis, "line_manifest", None)
    if (isinstance(manifest, list) and not manifest) or (
        snapshot.lineage_current and not snapshot.rows
    ):
        entry_block("empty_selection")
    if snapshot.lineage_current and batch_status == "ready_for_review" and snapshot.rows:
        states = [_value(row.validation_status) for row in snapshot.rows]
        if any(state != "valid" for state in states):
            entry_block("rows_not_ready")
        batch = snapshot.batch
        if (batch.total_rows != len(states) or batch.valid_rows != states.count("valid")
                or batch.invalid_rows != states.count("invalid")
                or batch.warning_rows != states.count("warning")):
            entry_block("counter_conflict")

    for line in ordered_lines:
        reason = _negative_reason(line)
        if reason:
            actions.append(_action("BLOCKER", "asset_review_line_blocked",
                                   _line_context(snapshot, line, reason)))
            blockers.append({"stage": STAGE, "reason_code": reason, "line_id": str(line.id)})
    unfinished_lines = [line for line in ordered_lines if not _finished(line)]
    unfinished_entry = (snapshot.lineage_current and batch_status in (
        "parsed", "validation_failed", "ready_for_review",
    ))
    if _value(snapshot.project.status) != "draft" and (unfinished_entry or unfinished_lines):
        entry_block("project_not_draft")

    if actions:
        result, action = "BLOCKED", actions[0]
    elif stale:
        fields = {key: str(entity.id) for key, entity in (
            ("official_intake_commit_id", snapshot.intake), ("result_id", snapshot.result),
            ("batch_id", snapshot.batch), ("staging_usage_id", snapshot.usage),
        ) if entity is not None}
        result, action = "STALE", _action("UNAVAILABLE", "asset_review_stale_recovery",
            _context(snapshot, "stale", stale[0]["reason_code"], reload_required=True, **fields))
    elif batch_status in ("parsed", "validation_failed", "ready_for_review"):
        fields = {"official_intake_commit_id": str(snapshot.intake.id),
                  "result_id": str(snapshot.result.id), "batch_id": str(snapshot.batch.id),
                  "staging_usage_id": str(snapshot.usage.id)}
        if batch_status == "ready_for_review":
            action = _action("PENDING", "asset_import_apply_confirm",
                _context(snapshot, "apply", "apply_required", **fields,
                         contract_version=CONTRACT_VERSION, confirmation_required=True))
        else:
            action = _action("PENDING", "asset_import_validate_pending",
                _context(snapshot, "validate", "validation_retry" if batch_status == "validation_failed"
                         else "validation_required", **fields))
        result = "INCOMPLETE"
    elif snapshot.seal_current and unfinished_lines:
        result, action = "INCOMPLETE", _action("PENDING", "asset_review_line_pending",
            _line_context(snapshot, unfinished_lines[0], "line_review_required"))
    elif snapshot.seal_current and membership_valid and ordered_lines:
        result, action = "COMPLETE", _action("NO_AUTHORIZED_DOWNSTREAM_ACTION", stage=None)
    else:
        # No valid available state can authorize progress without its committed seal.
        stale = [{"stage": STAGE, "reason_code": "seal_mismatch"}]
        result, action = "STALE", _action("UNAVAILABLE", "asset_review_stale_recovery",
            _context(snapshot, "stale", "seal_mismatch", reload_required=True))

    if action["semantic_route_key"] in {
        "asset_import_validate_pending", "asset_import_apply_confirm",
        "asset_review_line_pending", "asset_review_line_blocked",
    } and "workbench:edit" not in effective_permissions:
        action = _action("UNAVAILABLE", context=_context(snapshot, "permission", "permission_required"))
    return AssetReviewProviderResult(result, blockers, stale, action)
