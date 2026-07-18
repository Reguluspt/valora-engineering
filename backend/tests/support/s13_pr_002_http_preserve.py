"""Shared exact HTTP rejection preservation contract for S13-PR-002.

M-02: snapshot field sets equal SQLAlchemy persisted column keys.
M-03/N-01: type-preserving canonicalization (Enum-first; typed dict keys).
M-04/N-02: completed strong-helper *events* bound to node/status/error/bound.
"""
from __future__ import annotations

import copy
import re
import threading
import uuid
from dataclasses import asdict, dataclass
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
# N-02 runtime instrumentation — completed events (not counts alone)
# ---------------------------------------------------------------------------

_tls = threading.local()


@dataclass(frozen=True)
class StrongHelperEvent:
    nodeid: str
    status: int
    error_code: str
    reachability: str
    bound: str


@dataclass(frozen=True)
class StrongHelperExpectation:
    nodeid: str
    reachability: str
    bound: str
    error_code: str
    status: int
    accepted_mode: str  # "same_node" | "none"


def reset_strong_helper_context(expectation: StrongHelperExpectation | None = None) -> None:
    """Start a fresh per-node context (call from autouse fixture)."""
    _tls.events: list[StrongHelperEvent] = []
    _tls.expectation = expectation
    _tls.accepted_companion = False


def get_strong_helper_events() -> list[StrongHelperEvent]:
    return list(getattr(_tls, "events", []) or [])


def get_strong_helper_completed_calls() -> int:
    """Back-compat count of completed events."""
    return len(get_strong_helper_events())


def reset_strong_helper_calls() -> None:
    """Back-compat: clear events without setting expectation."""
    reset_strong_helper_context(None)


def record_accepted_companion() -> None:
    """Mark that the same-node N-accepted companion assertion ran successfully."""
    _tls.accepted_companion = True


def accepted_companion_recorded() -> bool:
    return bool(getattr(_tls, "accepted_companion", False))


def _record_strong_helper_completed(*, status: int, error_code: str) -> None:
    exp: StrongHelperExpectation | None = getattr(_tls, "expectation", None)
    if exp is None:
        # Not under a marked-node fixture — still record a minimal event for unit tests.
        nodeid = getattr(_tls, "nodeid", "<no-fixture>")
        reachability = getattr(_tls, "reachability", "")
        bound = getattr(_tls, "bound", "")
    else:
        nodeid = exp.nodeid
        reachability = exp.reachability
        bound = exp.bound
    events = getattr(_tls, "events", None)
    if events is None:
        _tls.events = []
        events = _tls.events
    events.append(
        StrongHelperEvent(
            nodeid=nodeid,
            status=status,
            error_code=error_code,
            reachability=reachability,
            bound=bound,
        )
    )


def event_as_dict(ev: StrongHelperEvent) -> dict[str, Any]:
    return asdict(ev)


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
# N-01: type-preserving deep canonicalization (Enum before scalar bases)
# ---------------------------------------------------------------------------


def _sort_key_for_canonical(item: Any) -> str:
    """Deterministic sort key that does not collapse types."""
    return repr(item)


def canonical(value: Any) -> Any:
    """Deterministic, type-preserving deep form for snapshot equality.

    Enum is handled *before* bool/int/str so string-backed Enums and IntEnums
    do not collapse into their scalar bases. Dict keys use the same typed
    canonicalizer (never str(k)).
    """
    if value is None:
        return ("none", None)
    # Enum before bool/int/str — str Enum and IntEnum are subclasses of str/int.
    if isinstance(value, Enum):
        et = type(value)
        return (
            "enum",
            et.__module__,
            et.__qualname__,
            canonical(value.value),
        )
    if isinstance(value, bool):  # before int
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value)
    if isinstance(value, Decimal):
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
    if isinstance(value, dict):
        items = tuple(
            sorted(
                ((canonical(k), canonical(v)) for k, v in value.items()),
                key=_sort_key_for_canonical,
            )
        )
        return ("dict", items)
    if isinstance(value, list):
        return ("list", tuple(canonical(v) for v in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(canonical(v) for v in value))
    if isinstance(value, set):
        return ("set", tuple(sorted((canonical(v) for v in value), key=_sort_key_for_canonical)))
    raise TypeError(f"unsupported snapshot value type: {type(value)!r}")


def assert_canonical_distinguishes_collisions() -> None:
    """Self-test: known type collisions are not collapsed (incl. Enum/dict keys)."""
    from enum import IntEnum

    from app.modules.project_master_data.models import (
        AssetLineReviewStatus,
        ImportBatchStatus,
    )

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

    # Real string-backed project Enums vs scalar strings
    assert canonical(ImportBatchStatus.CREATED) != canonical("created")
    assert canonical(AssetLineReviewStatus.PENDING) != canonical("pending")

    class LocalInt(IntEnum):
        ONE = 1

    assert canonical(LocalInt.ONE) != canonical(1)

    class OtherCreated(str, Enum):
        CREATED = "created"

    # Same member value, different Enum class
    assert canonical(ImportBatchStatus.CREATED) != canonical(OtherCreated.CREATED)

    # Typed dict keys
    u = uuid.UUID(int=7)
    assert canonical({1: "x"}) != canonical({"1": "x"})
    assert canonical({u: "x"}) != canonical({str(u): "x"})

    # Stable ordering regardless of insertion order
    assert canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1})

    # Unsupported type is fail-closed
    try:
        canonical(object())
        raise AssertionError("expected TypeError for unsupported type")
    except TypeError:
        pass

    # deep copy isolation
    src = {"nested": [1, {"k": Decimal("2.5")}]}
    c1 = canonical(src)
    src["nested"].append(3)
    src["nested"][1]["k"] = Decimal("9")
    assert c1 == canonical({"nested": [1, {"k": Decimal("2.5")}]})


# ---------------------------------------------------------------------------
# N-04: exact collect-count parsing
# ---------------------------------------------------------------------------


_COLLECT_SLASH = re.compile(r"(?m)^(\d+)/(\d+) tests? collected\b")
_COLLECT_PLAIN = re.compile(r"(?m)^(\d+) tests? collected\b")


def parse_pytest_collect_selected_count(output: str) -> int:
    """Parse selected item count from pytest --collect-only -q summary.

    Anchored to start-of-line so ``148/831`` is not accepted as ``48``.
    """
    m = _COLLECT_SLASH.search(output)
    if m:
        return int(m.group(1))
    m = _COLLECT_PLAIN.search(output)
    if m:
        return int(m.group(1))
    raise ValueError(f"no pytest collect summary found in output:\n{output[-500:]}")


def assert_pytest_collect_count_exactly(
    output: str,
    *,
    expected: int,
    returncode: int,
) -> int:
    """Require subprocess success and exact selected count."""
    if returncode != 0:
        raise AssertionError(
            f"pytest collect subprocess failed with returncode={returncode}:\n{output[-800:]}"
        )
    try:
        n = parse_pytest_collect_selected_count(output)
    except ValueError as e:
        raise AssertionError(str(e)) from e
    if n != expected:
        raise AssertionError(f"expected collect count {expected}, got {n}")
    return n


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

    Records one completed StrongHelperEvent only after status, error_code and
    full equality all succeed (N-02).
    """
    assert res.status_code == status, res.text
    body = res.json()
    detail = body.get("detail")
    assert isinstance(detail, dict), f"detail must be mapping, got {type(detail)!r}: {detail!r}"
    assert detail.get("error_code") == error_code, detail
    assert_source_intake_preserve(db, fake_storage, snap)
    _record_strong_helper_completed(status=status, error_code=error_code)


def assert_accepted_source_upload(res, *, status: int = 201) -> None:
    """Assert successful companion upload and record same-node accepted evidence."""
    assert res.status_code == status, getattr(res, "text", res)
    record_accepted_companion()


# Back-compat name used by older suites/eleventh self-test imports.
def assert_audit_snapshot_detects_mutations() -> None:
    """Deprecated hand-built proof — prefer DB-backed twelfth probes."""
    assert_canonical_distinguishes_collisions()
    base = [{"id": "1", "payload": {"k": "v"}}]
    assert base != copy.deepcopy(base) + [{"id": "2"}]
    assert base != []
    mutated = copy.deepcopy(base)
    mutated[0]["payload"] = {"k": "mutated"}
    assert base != mutated
