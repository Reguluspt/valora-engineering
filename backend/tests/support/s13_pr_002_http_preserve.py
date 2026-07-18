"""Shared exact HTTP rejection preservation contract for S13-PR-002.

Used by every retained endpoint N+1 rejection node so weaker “count-only /
no-Reserved-audit / key-set-only” helpers cannot silently reappear.

M-02: snapshot field sets equal SQLAlchemy persisted column keys.
M-03: type-preserving canonicalization (no lossy default=str JSON).
M-04: runtime instrumentation of completed strong-helper calls.
"""
from __future__ import annotations

import copy
import threading
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.modules.excel_import.models import ImportSourceArtifact
from app.modules.project_master_data.models import (
    AuditEvent,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ProjectAssetLine,
)


# ---------------------------------------------------------------------------
# M-04 runtime instrumentation (completed strong-helper calls only)
# ---------------------------------------------------------------------------

_tls = threading.local()


def reset_strong_helper_calls() -> None:
    _tls.completed = 0


def get_strong_helper_completed_calls() -> int:
    return int(getattr(_tls, "completed", 0))


def _record_strong_helper_completed() -> None:
    _tls.completed = get_strong_helper_completed_calls() + 1


# ---------------------------------------------------------------------------
# M-02: field sets = mapper column keys
# ---------------------------------------------------------------------------


def persisted_column_keys(model: type) -> tuple[str, ...]:
    """Sorted persisted table column attribute keys (exclude relationships/hybrids)."""
    return tuple(sorted(c.key for c in sa_inspect(model).mapper.column_attrs))


ARTIFACT_FIELDS = persisted_column_keys(ImportSourceArtifact)
BATCH_FIELDS = persisted_column_keys(ProjectAssetImportBatch)
STAGING_FIELDS = persisted_column_keys(ProjectAssetImportStagingRow)
LINE_FIELDS = persisted_column_keys(ProjectAssetLine)
AUDIT_FIELDS = persisted_column_keys(AuditEvent)

_MODEL_FIELDS: dict[type, tuple[str, ...]] = {
    ImportSourceArtifact: ARTIFACT_FIELDS,
    ProjectAssetImportBatch: BATCH_FIELDS,
    ProjectAssetImportStagingRow: STAGING_FIELDS,
    ProjectAssetLine: LINE_FIELDS,
    AuditEvent: AUDIT_FIELDS,
}


def assert_field_sets_match_mappers() -> None:
    """Executable guard: module field tuples == live mapper column keys."""
    for model, fields in _MODEL_FIELDS.items():
        live = set(persisted_column_keys(model))
        guarded = set(fields)
        assert guarded == live, (
            f"{model.__name__}: guarded={sorted(guarded)} live={sorted(live)} "
            f"missing={sorted(live - guarded)} extra={sorted(guarded - live)}"
        )


# ---------------------------------------------------------------------------
# M-03: type-preserving deep canonicalization
# ---------------------------------------------------------------------------


def canonical(value: Any) -> Any:
    """Deterministic, type-preserving deep form for snapshot equality.

    Distinguishes int/float, UUID/str, Decimal/number, list/tuple, bytes/str,
    timezone-aware/naive datetime, and Enum vs scalar value.
    """
    if value is None:
        return ("none", None)
    if isinstance(value, bool):  # before int (bool is int subclass)
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value)
    if isinstance(value, Decimal):
        # preserve exact decimal text (no float coercion)
        return ("decimal", format(value, "f"))
    if isinstance(value, uuid.UUID):
        return ("uuid", str(value))
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    if isinstance(value, bytearray):
        return ("bytearray", bytes(value).hex())
    if isinstance(value, memoryview):
        return ("bytes", value.tobytes().hex())
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, datetime):
        return (
            "datetime",
            value.isoformat(),
            "aware" if value.tzinfo is not None else "naive",
        )
    if isinstance(value, date):
        return ("date", value.isoformat())
    if isinstance(value, time):
        return (
            "time",
            value.isoformat(),
            "aware" if value.tzinfo is not None else "naive",
        )
    if isinstance(value, Enum):
        return ("enum", type(value).__name__, canonical(value.value))
    if isinstance(value, dict):
        items = sorted(((str(k), canonical(v)) for k, v in value.items()), key=lambda kv: kv[0])
        return ("dict", tuple(items))
    if isinstance(value, list):
        return ("list", tuple(canonical(v) for v in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(canonical(v) for v in value))
    if isinstance(value, set):
        return ("set", tuple(sorted((canonical(v) for v in value), key=repr)))
    # Fail closed rather than str()-collapsing unknown types.
    raise TypeError(f"unsupported snapshot value type: {type(value)!r}")


def assert_canonical_distinguishes_collisions() -> None:
    """Self-test: known type collisions are not collapsed."""
    assert canonical(1) != canonical(1.0)
    assert canonical(uuid.UUID(int=1)) != canonical(str(uuid.UUID(int=1)))
    assert canonical(Decimal("1")) != canonical(1)
    assert canonical(Decimal("1")) != canonical(1.0)
    assert canonical(Decimal("1")) != canonical("1")
    assert canonical([1]) != canonical((1,))
    assert canonical(b"x") != canonical("x")
    aware = datetime(2026, 7, 18, 12, 0, 0, tzinfo=__import__("datetime").timezone.utc)
    naive = datetime(2026, 7, 18, 12, 0, 0)
    assert canonical(aware) != canonical(naive)
    # deep copy isolation
    src = {"nested": [1, {"k": Decimal("2.5")}]}
    c1 = canonical(src)
    src["nested"].append(3)
    src["nested"][1]["k"] = Decimal("9")
    assert c1 == canonical({"nested": [1, {"k": Decimal("2.5")}]})


# ---------------------------------------------------------------------------
# Row serializers — keys must equal field set exactly
# ---------------------------------------------------------------------------


def _row(model_obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in fields:
        out[name] = canonical(getattr(model_obj, name))
    assert set(out.keys()) == set(fields), (
        f"serializer keys {sorted(out)} != fields {sorted(fields)}"
    )
    return out


def _row_artifact(a: ImportSourceArtifact) -> dict[str, Any]:
    return _row(a, ARTIFACT_FIELDS)


def _row_batch(b: ProjectAssetImportBatch) -> dict[str, Any]:
    return _row(b, BATCH_FIELDS)


def _row_staging(s: ProjectAssetImportStagingRow) -> dict[str, Any]:
    return _row(s, STAGING_FIELDS)


def _row_line(line: ProjectAssetLine) -> dict[str, Any]:
    return _row(line, LINE_FIELDS)


def _row_audit(a: AuditEvent) -> dict[str, Any]:
    return _row(a, AUDIT_FIELDS)


def _as_uuid(value: Any):
    """Accept UUID instances or string UUIDs for SQLAlchemy UUID bind params."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def snapshot_source_intake_preserve(
    db: Session,
    fake_storage,
    *,
    project_id,
    batch_id,
) -> dict[str, Any]:
    """Immutable deep snapshot of all preserve-relevant state before an HTTP reject."""
    assert_field_sets_match_mappers()
    db.expire_all()
    pid = _as_uuid(project_id)
    bid = _as_uuid(batch_id)
    arts = (
        db.query(ImportSourceArtifact)
        .order_by(ImportSourceArtifact.generation.asc(), ImportSourceArtifact.id.asc())
        .all()
    )
    batches = (
        db.query(ProjectAssetImportBatch)
        .filter(ProjectAssetImportBatch.id == bid)
        .all()
    )
    staging = (
        db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == bid)
        .order_by(
            ProjectAssetImportStagingRow.source_row_number.asc(),
            ProjectAssetImportStagingRow.id.asc(),
        )
        .all()
    )
    lines = (
        db.query(ProjectAssetLine)
        .filter(ProjectAssetLine.project_id == pid)
        .order_by(ProjectAssetLine.id.asc())
        .all()
    )
    audits = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    # Deep-copy object store so later mutations cannot alias snap contents.
    objects = {k: bytes(v) for k, v in fake_storage._objects.items()}
    content_types = dict(fake_storage._content_types)
    return {
        "objects": objects,
        "content_types": content_types,
        "artifacts": [_row_artifact(a) for a in arts],
        "batches": [_row_batch(b) for b in batches],
        "staging": [_row_staging(s) for s in staging],
        "lines": [_row_line(ln) for ln in lines],
        "audits": [_row_audit(a) for a in audits],
        "project_id": str(pid) if pid is not None else None,
        "batch_id": str(bid) if bid is not None else None,
    }


def assert_source_intake_preserve(db: Session, fake_storage, snap: dict[str, Any]) -> None:
    """Exact equality of every snapshot component after an HTTP rejection."""
    db.expire_all()
    after = snapshot_source_intake_preserve(
        db,
        fake_storage,
        project_id=snap["project_id"],
        batch_id=snap["batch_id"],
    )
    assert after["objects"] == snap["objects"], "object-store bytes changed on reject"
    assert after["content_types"] == snap["content_types"], "content_types changed on reject"
    assert after["artifacts"] == snap["artifacts"], "artifact rows changed on reject"
    assert after["batches"] == snap["batches"], "batch fields changed on reject"
    assert after["staging"] == snap["staging"], "staging rows changed on reject"
    assert after["lines"] == snap["lines"], "official lines changed on reject"
    assert after["audits"] == snap["audits"], "audit snapshot changed on reject"


def assert_http_rejection_preserve(
    res,
    *,
    status: int,
    error_code: str,
    db: Session,
    fake_storage,
    snap: dict[str, Any],
) -> None:
    """Unconditional status/error_code + full preservation contract.

    Records one *completed* strong-helper call only after status, error_code and
    full equality all succeed (M-04).
    """
    assert res.status_code == status, res.text
    body = res.json()
    detail = body.get("detail")
    assert isinstance(detail, dict), f"detail must be mapping, got {type(detail)!r}: {detail!r}"
    assert detail.get("error_code") == error_code, detail
    assert_source_intake_preserve(db, fake_storage, snap)
    _record_strong_helper_completed()


# Back-compat name used by older suites/eleventh self-test imports.
def assert_audit_snapshot_detects_mutations() -> None:
    """Deprecated hand-built proof — prefer DB-backed twelfth probes.

    Kept as a thin wrapper so import sites do not break; real proof is M-03 suite.
    """
    assert_canonical_distinguishes_collisions()
    # Minimal list inequality still documented for supplementary lint.
    base = [{"id": "1", "payload": {"k": "v"}}]
    assert base != copy.deepcopy(base) + [{"id": "2"}]
    assert base != []
    mutated = copy.deepcopy(base)
    mutated[0]["payload"] = {"k": "mutated"}
    assert base != mutated
