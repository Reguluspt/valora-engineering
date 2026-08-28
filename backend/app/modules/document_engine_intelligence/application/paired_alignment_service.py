"""Content-based, review-only alignment for extracted Excel and report rows."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Sequence

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.modules.excel_import.models import (
    DossierAlignmentRun,
    DossierAlignmentState,
    DossierExtractedRow,
    DossierExtractedTable,
    DossierExtractionSnapshot,
    DossierRowAlignment,
    DossierSourceKind,
    DossierTableRole,
    TaskJob,
    TaskJobStatus,
)

_ALGORITHM_VERSION = "paired-content-v1"
_CANDIDATE_THRESHOLD = 0.85
_MIN_IDENTITY_SCORE = 0.45
_AMBIGUITY_DELTA = 0.08


class DossierAlignmentError(Exception):
    def __init__(self, code: str, detail: str, *, retryable: bool = False):
        self.code = code
        self.detail = detail
        self.retryable = retryable
        super().__init__(detail)


@dataclass(frozen=True)
class RowCandidate:
    row: DossierExtractedRow
    score: float
    basis: dict[str, Any]
    conflicts: tuple[dict[str, Any], ...]


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("đ", "d")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _tokens(value: Any) -> set[str]:
    return set(_fold(value).split())


def _similarity(left: Any, right: Any) -> float:
    folded_left = _fold(left)
    folded_right = _fold(right)
    if not folded_left or not folded_right:
        return 0.0
    sequence = SequenceMatcher(None, folded_left, folded_right).ratio()
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    return max(sequence, jaccard)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    compact = re.sub(r"[^0-9,.-]", "", str(value))
    if not compact:
        return None
    if compact.count(",") == 1 and "." not in compact:
        compact = compact.replace(",", ".")
    else:
        compact = compact.replace(",", "")
    try:
        return float(compact)
    except ValueError:
        return None


def _technical_text(fields: dict[str, Any]) -> str:
    technical = fields.get("technical_attributes") or {}
    if not isinstance(technical, dict):
        return _fold(technical)
    return _fold(" ".join(f"{key} {value}" for key, value in sorted(technical.items())))


def _score_pair(
    excel_row: DossierExtractedRow,
    target_row: DossierExtractedRow,
    *,
    excel_position: int,
    target_position: int,
    target_count: int,
) -> RowCandidate | None:
    excel = excel_row.normalized_fields or {}
    target = target_row.normalized_fields or {}
    stt_left = _fold(excel.get("stt"))
    stt_right = _fold(target.get("stt"))
    stt_exact = bool(stt_left and stt_right and stt_left == stt_right)
    name_similarity = _similarity(excel.get("name"), target.get("name"))
    identity_signal = stt_exact or name_similarity >= _MIN_IDENTITY_SCORE
    if not identity_signal:
        return None

    unit_left = _fold(excel.get("unit"))
    unit_right = _fold(target.get("unit"))
    unit_known = bool(unit_left and unit_right)
    unit_exact = unit_known and unit_left == unit_right
    quantity_left = _number(excel.get("quantity"))
    quantity_right = _number(target.get("quantity"))
    quantity_known = quantity_left is not None and quantity_right is not None
    quantity_equal = bool(
        quantity_known
        and abs(quantity_left - quantity_right) <= max(0.0001, abs(quantity_left) * 0.001)
    )
    technical_similarity = _similarity(_technical_text(excel), _technical_text(target))
    order_distance = abs(excel_position - target_position)
    order_denominator = max(1, target_count - 1)
    order_score = max(0.0, 1.0 - order_distance / order_denominator)

    score = 0.0
    weight = 0.0
    if stt_left and stt_right:
        score += 0.30 if stt_exact else 0.0
        weight += 0.30
    if excel.get("name") and target.get("name"):
        score += 0.35 * name_similarity
        weight += 0.35
    if unit_known:
        score += 0.15 if unit_exact else 0.0
        weight += 0.15
    if quantity_known:
        score += 0.10 if quantity_equal else 0.0
        weight += 0.10
    if _technical_text(excel) and _technical_text(target):
        score += 0.05 * technical_similarity
        weight += 0.05
    # Order is only a weak tie-breaker after an STT/name identity signal exists.
    score += 0.05 * order_score
    weight += 0.05
    normalized_score = min(1.0, score / weight if weight else 0.0)

    conflicts: list[dict[str, Any]] = []
    if unit_known and not unit_exact:
        conflicts.append(
            {
                "code": "unit_mismatch",
                "excel_value": excel.get("unit"),
                "report_value": target.get("unit"),
            }
        )
    if quantity_known and not quantity_equal:
        conflicts.append(
            {
                "code": "quantity_or_rounding_mismatch",
                "excel_value": excel.get("quantity"),
                "report_value": target.get("quantity"),
            }
        )
    return RowCandidate(
        row=target_row,
        score=normalized_score,
        basis={
            "stt_exact": stt_exact,
            "name_similarity": round(name_similarity, 4),
            "unit_exact": unit_exact if unit_known else None,
            "quantity_equal": quantity_equal if quantity_known else None,
            "technical_similarity": round(technical_similarity, 4),
            "order_score": round(order_score, 4),
            "order_used_only_as_tiebreaker": True,
            "excel_locator": excel_row.locator_json,
            "report_locator": target_row.locator_json,
        },
        conflicts=tuple(conflicts),
    )


def _best_candidate(
    excel_row: DossierExtractedRow,
    targets: Sequence[DossierExtractedRow],
    *,
    excel_position: int,
) -> tuple[RowCandidate | None, bool]:
    candidates = [
        candidate
        for target_position, target in enumerate(targets)
        if (
            candidate := _score_pair(
                excel_row,
                target,
                excel_position=excel_position,
                target_position=target_position,
                target_count=len(targets),
            )
        )
        is not None
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)
    if not candidates:
        return None, False
    ambiguous = len(candidates) > 1 and candidates[0].score - candidates[1].score < _AMBIGUITY_DELTA
    return candidates[0], ambiguous


def _rows_for_role(
    db: Session,
    *,
    org_id: uuid.UUID,
    bundle_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    role: str,
) -> list[DossierExtractedRow]:
    return (
        db.query(DossierExtractedRow)
        .join(
            DossierExtractedTable,
            DossierExtractedTable.id == DossierExtractedRow.extracted_table_id,
        )
        .filter(
            DossierExtractedRow.organization_id == org_id,
            DossierExtractedRow.dossier_bundle_id == bundle_id,
            DossierExtractedRow.is_header.is_(False),
            DossierExtractedTable.extraction_snapshot_id == snapshot_id,
            DossierExtractedTable.table_role_candidate == role,
        )
        .order_by(DossierExtractedTable.table_index, DossierExtractedRow.row_index)
        .all()
    )


def _assert_live_alignment_job(
    job: TaskJob | None,
    *,
    bundle_id: uuid.UUID,
    excel_snapshot_id: uuid.UUID,
    report_snapshot_id: uuid.UUID,
    generation_token: int,
) -> None:
    now = datetime.now(timezone.utc)
    lease = job.lease_expires_at if job is not None else None
    if lease is not None and lease.tzinfo is None:
        lease = lease.replace(tzinfo=timezone.utc)
    payload = job.payload if job is not None else {}
    if (
        job is None
        or job.job_type != "dossier_alignment"
        or job.status != TaskJobStatus.CLAIMED.value
        or job.generation_token != generation_token
        or lease is None
        or lease <= now
        or payload.get("dossier_bundle_id") != str(bundle_id)
        or payload.get("excel_snapshot_id") != str(excel_snapshot_id)
        or payload.get("report_snapshot_id") != str(report_snapshot_id)
    ):
        raise DossierAlignmentError(
            "stale_alignment_job", "Job alignment không còn lease/generation hợp lệ."
        )


def generate_dossier_row_alignments(
    db: Session,
    *,
    org_id: uuid.UUID,
    dossier_bundle_id: uuid.UUID,
    excel_snapshot_id: uuid.UUID,
    report_snapshot_id: uuid.UUID,
    job_id: uuid.UUID,
    generation_token: int,
) -> DossierAlignmentRun:
    """Generate reviewable candidates from real extracted row content; never auto-confirm."""
    snapshots = (
        db.query(DossierExtractionSnapshot)
        .filter(
            DossierExtractionSnapshot.organization_id == org_id,
            DossierExtractionSnapshot.dossier_bundle_id == dossier_bundle_id,
            DossierExtractionSnapshot.id.in_([excel_snapshot_id, report_snapshot_id]),
        )
        .all()
    )
    by_id = {snapshot.id: snapshot for snapshot in snapshots}
    excel_snapshot = by_id.get(excel_snapshot_id)
    report_snapshot = by_id.get(report_snapshot_id)
    if excel_snapshot is None or report_snapshot is None:
        raise _error(404, "resource_not_found", "Không tìm thấy snapshot extraction.")
    if excel_snapshot.source_kind != DossierSourceKind.EXCEL.value:
        raise _error(422, "invalid_excel_snapshot", "Snapshot Excel không hợp lệ.")
    if report_snapshot.source_kind != DossierSourceKind.DOCX.value:
        raise _error(422, "invalid_report_snapshot", "Snapshot báo cáo không hợp lệ.")

    pair_digest = _digest(
        {
            "excel_snapshot_id": str(excel_snapshot.id),
            "excel_digest": excel_snapshot.extraction_digest_sha256,
            "report_snapshot_id": str(report_snapshot.id),
            "report_digest": report_snapshot.extraction_digest_sha256,
            "algorithm_version": _ALGORITHM_VERSION,
        }
    )
    preflight_job = (
        db.query(TaskJob)
        .filter(TaskJob.organization_id == org_id, TaskJob.id == job_id)
        .populate_existing()
        .first()
    )
    _assert_live_alignment_job(
        preflight_job,
        bundle_id=dossier_bundle_id,
        excel_snapshot_id=excel_snapshot_id,
        report_snapshot_id=report_snapshot_id,
        generation_token=generation_token,
    )
    existing = (
        db.query(DossierAlignmentRun)
        .filter(
            DossierAlignmentRun.organization_id == org_id,
            DossierAlignmentRun.dossier_bundle_id == dossier_bundle_id,
            DossierAlignmentRun.source_pair_digest_sha256 == pair_digest,
            DossierAlignmentRun.algorithm_version == _ALGORITHM_VERSION,
        )
        .first()
    )
    if existing is not None:
        db.rollback()
        return existing

    excel_rows = _rows_for_role(
        db,
        org_id=org_id,
        bundle_id=dossier_bundle_id,
        snapshot_id=excel_snapshot_id,
        role=DossierTableRole.EXCEL_CUSTOMER_ASSET_TABLE.value,
    )
    technical_rows = _rows_for_role(
        db,
        org_id=org_id,
        bundle_id=dossier_bundle_id,
        snapshot_id=report_snapshot_id,
        role=DossierTableRole.WORD_TECHNICAL_ASSET_TABLE.value,
    )
    comparison_rows = _rows_for_role(
        db,
        org_id=org_id,
        bundle_id=dossier_bundle_id,
        snapshot_id=report_snapshot_id,
        role=DossierTableRole.WORD_QUOTE_COMPARISON_TABLE.value,
    )
    final_rows = _rows_for_role(
        db,
        org_id=org_id,
        bundle_id=dossier_bundle_id,
        snapshot_id=report_snapshot_id,
        role=DossierTableRole.WORD_FINAL_RESULT_TABLE.value,
    )
    if not excel_rows:
        raise DossierAlignmentError(
            "excel_asset_rows_missing", "Không tìm thấy dòng tài sản Excel để alignment."
        )

    candidates: list[dict[str, Any]] = []
    counts = {state.value: 0 for state in DossierAlignmentState}
    for excel_position, excel_row in enumerate(excel_rows):
        technical, technical_ambiguous = _best_candidate(
            excel_row, technical_rows, excel_position=excel_position
        )
        comparison, comparison_ambiguous = _best_candidate(
            excel_row, comparison_rows, excel_position=excel_position
        )
        final, final_ambiguous = _best_candidate(
            excel_row, final_rows, excel_position=excel_position
        )
        selected = {
            "technical": technical,
            "comparison": comparison,
            "final_result": final,
        }
        present = [candidate for candidate in selected.values() if candidate is not None]
        conflicts: list[dict[str, Any]] = [
            conflict for candidate in present for conflict in candidate.conflicts
        ]
        ambiguous_roles = [
            role
            for role, ambiguous in {
                "technical": technical_ambiguous,
                "comparison": comparison_ambiguous,
                "final_result": final_ambiguous,
            }.items()
            if ambiguous
        ]
        if ambiguous_roles:
            conflicts.append({"code": "ambiguous_candidates", "roles": ambiguous_roles})
        confidence = sum(candidate.score for candidate in present) / len(present) if present else 0.0
        if not present:
            state = DossierAlignmentState.UNRESOLVED.value
        elif confidence >= _CANDIDATE_THRESHOLD and not conflicts:
            state = DossierAlignmentState.CANDIDATE.value
        else:
            state = DossierAlignmentState.REVIEW_REQUIRED.value
        counts[state] += 1
        candidates.append(
            {
                "excel_row": excel_row,
                "technical": technical,
                "comparison": comparison,
                "final": final,
                "state": state,
                "confidence": confidence,
                "match_basis": {
                    role: None
                    if candidate is None
                    else {"score": round(candidate.score, 4), **candidate.basis}
                    for role, candidate in selected.items()
                },
                "conflicts": conflicts,
            }
        )

    job = (
        db.query(TaskJob)
        .filter(TaskJob.organization_id == org_id, TaskJob.id == job_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    _assert_live_alignment_job(
        job,
        bundle_id=dossier_bundle_id,
        excel_snapshot_id=excel_snapshot_id,
        report_snapshot_id=report_snapshot_id,
        generation_token=generation_token,
    )
    existing = (
        db.query(DossierAlignmentRun)
        .filter(
            DossierAlignmentRun.organization_id == org_id,
            DossierAlignmentRun.dossier_bundle_id == dossier_bundle_id,
            DossierAlignmentRun.source_pair_digest_sha256 == pair_digest,
            DossierAlignmentRun.algorithm_version == _ALGORITHM_VERSION,
        )
        .first()
    )
    if existing is not None:
        db.commit()
        return existing

    run_status = (
        DossierAlignmentState.CANDIDATE.value
        if counts[DossierAlignmentState.CANDIDATE.value] == len(excel_rows)
        else DossierAlignmentState.REVIEW_REQUIRED.value
    )
    run = DossierAlignmentRun(
        organization_id=org_id,
        dossier_bundle_id=dossier_bundle_id,
        excel_snapshot_id=excel_snapshot_id,
        report_snapshot_id=report_snapshot_id,
        algorithm_version=_ALGORITHM_VERSION,
        source_pair_digest_sha256=pair_digest,
        created_by_job_id=job_id,
        generation_token=generation_token,
        status=run_status,
        total_excel_rows=len(excel_rows),
        candidate_count=counts[DossierAlignmentState.CANDIDATE.value],
        review_required_count=counts[DossierAlignmentState.REVIEW_REQUIRED.value],
        unresolved_count=counts[DossierAlignmentState.UNRESOLVED.value],
    )
    db.add(run)
    db.flush()
    db.add_all(
        [
            DossierRowAlignment(
                organization_id=org_id,
                dossier_bundle_id=dossier_bundle_id,
                alignment_run_id=run.id,
                excel_row_id=item["excel_row"].id,
                technical_row_id=(item["technical"].row.id if item["technical"] else None),
                comparison_row_id=(
                    item["comparison"].row.id if item["comparison"] else None
                ),
                final_result_row_id=(item["final"].row.id if item["final"] else None),
                state=item["state"],
                confidence_score=item["confidence"],
                match_basis=item["match_basis"],
                conflicts=item["conflicts"],
            )
            for item in candidates
        ]
    )
    log_audit_event(
        db,
        event_name="DossierRowAlignmentCandidatesGenerated",
        entity_type="DossierAlignmentRun",
        entity_id=run.id,
        organization_id=org_id,
        command_name="GenerateDossierRowAlignments",
        correlation_id=job.correlation_id,
        payload={
            "dossier_bundle_id": str(dossier_bundle_id),
            "excel_snapshot_id": str(excel_snapshot_id),
            "report_snapshot_id": str(report_snapshot_id),
            "source_pair_digest_sha256": pair_digest,
            "algorithm_version": _ALGORITHM_VERSION,
            "total_excel_rows": run.total_excel_rows,
            "candidate_count": run.candidate_count,
            "review_required_count": run.review_required_count,
            "unresolved_count": run.unresolved_count,
            "generation_token": generation_token,
            "auto_confirmed": 0,
        },
    )
    db.commit()
    db.refresh(run)
    return run
