"""S13-PR-002 HTTP rejection preservation + independent evidence-gate runtime.

R-03/R-04: actual_* never copied from ledger; observed_* from real HTTP response.
"""

from __future__ import annotations

import re
import hashlib
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.modules.excel_import.models import ImportSourceArtifact
from app.modules.excel_import.application import source_artifact_service
from app.modules.excel_import.domain.source_artifact import SourceArtifactLimits
from app.modules.project_master_data.models import (
    AuditEvent,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ProjectAssetLine,
)

# ---------------------------------------------------------------------------
# Runtime context (TLS)
# ---------------------------------------------------------------------------

_tls = threading.local()


@dataclass(frozen=True)
class CaseInput:
    """B: one immutable input drives both limits and artifact reachability."""

    reachability: str
    bound: str

    def default_limit_value(self) -> int:
        if self.bound not in SourceArtifactLimits.__dataclass_fields__:
            raise AssertionError(f"unknown SourceArtifactLimits field: {self.bound}")
        value = getattr(SourceArtifactLimits(), self.bound)
        if not isinstance(value, int):
            raise AssertionError(f"non-integer SourceArtifactLimits field: {self.bound}")
        return value

    def build_artifact(
        self,
        *,
        intake: Any = None,
        xlsx: Any = None,
        xls: Any = None,
    ) -> bytes:
        """Build bytes through the branch selected by this exact CaseInput."""
        builders = {"intake": intake, "xlsx": xlsx, "xls": xls}
        if self.reachability not in builders:
            raise AssertionError(f"unsupported reachability: {self.reachability}")
        supplied = [name for name, builder in builders.items() if builder is not None]
        if supplied != [self.reachability]:
            raise AssertionError(
                f"CaseInput reachability {self.reachability!r} requires only its "
                f"matching artifact builder; supplied={supplied}"
            )
        builder = builders[self.reachability]
        raw = builder() if callable(builder) else builder
        if not isinstance(raw, (bytes, bytearray, memoryview)):
            raise AssertionError(f"artifact builder returned {type(raw)!r}, expected bytes")
        payload = bytes(raw)
        register_case_input(self)
        receipts = getattr(_tls, "artifact_receipts", None)
        if receipts is None:
            _tls.artifact_receipts = []
            receipts = _tls.artifact_receipts
        receipts.append(
            ArtifactReceipt(
                case=self,
                reachability=self.reachability,
                payload=payload,
                sha256=hashlib.sha256(payload).hexdigest(),
                size=len(payload),
            )
        )
        return payload


@dataclass(frozen=True)
class ArtifactReceipt:
    case: CaseInput
    reachability: str
    payload: bytes
    sha256: str
    size: int


@dataclass(frozen=True)
class AppliedLimitBinding:
    case: CaseInput
    limits: SourceArtifactLimits
    limit_value: int


@dataclass(frozen=True)
class RejectionEvent:
    actual_nodeid: str
    actual_case_id: str
    actual_reachability: str
    actual_bound: str
    declared_reachability: str
    declared_bound: str
    observed_status: int
    observed_error_code: str
    row_id: str


@dataclass(frozen=True)
class AcceptedEvent:
    row_id: str
    actual_nodeid: str
    actual_case_id: str
    observed_accepted_status: int


def clear_evidence_context() -> None:
    _tls.rejection_events = []
    _tls.accepted_events = []
    _tls.case_input = None
    _tls.actual_nodeid = None
    _tls.actual_case_id = None
    _tls.limit_binding = None
    _tls.artifact_receipts = []
    _tls.ledger_row = None
    _tls.declared = None


def set_runtime_identity(nodeid: str, case_id: str) -> None:
    _tls.actual_nodeid = nodeid
    _tls.actual_case_id = case_id


def set_runtime_node(nodeid: str) -> None:
    """Legacy alias; new gate binds nodeid and runtime case id together."""
    set_runtime_identity(nodeid, nodeid.split("::")[-1])


def set_ledger_row(row: dict[str, Any]) -> None:
    _tls.ledger_row = dict(row)
    _tls.declared = {
        "reachability": row["reachability"],
        "bound": row["bound"],
        "reject_status": row["reject_status"],
        "reject_error_code": row["reject_error_code"],
        "row_id": row["row_id"],
        "accepted_execution": row["accepted_execution"],
        "accepted_evidence_row_id": row["accepted_evidence_row_id"],
        "accepted_status": row["accepted_status"],
    }


def register_case_input(case: CaseInput) -> CaseInput:
    """Register B — must use the same values that configure limits/payload."""
    existing = getattr(_tls, "case_input", None)
    if existing is not None and existing is not case:
        raise AssertionError("one marked node must use one identical CaseInput object")
    _tls.case_input = case
    return case


@contextmanager
def source_case_limits(
    case: CaseInput,
    limit_value: int,
    **additional_limits: int,
):
    """Apply production's real HTTP limit seam from the exact CaseInput."""
    if case.bound in additional_limits:
        raise AssertionError(
            f"duplicate target bound {case.bound!r}: CaseInput must be sole authority"
        )
    if case.bound not in SourceArtifactLimits.__dataclass_fields__:
        raise AssertionError(f"unknown SourceArtifactLimits field: {case.bound}")
    register_case_input(case)
    if getattr(_tls, "limit_binding", None) is not None:
        raise AssertionError("only one active source_case_limits binding is allowed")
    limits = SourceArtifactLimits(**{case.bound: limit_value, **additional_limits})
    binding = AppliedLimitBinding(case=case, limits=limits, limit_value=limit_value)
    _tls.limit_binding = binding
    source_artifact_service.set_source_limits_override(limits)
    try:
        yield limits
    finally:
        source_artifact_service.set_source_limits_override(None)


def get_case_input() -> CaseInput | None:
    return getattr(_tls, "case_input", None)


def get_rejection_events() -> list[RejectionEvent]:
    return list(getattr(_tls, "rejection_events", []) or [])


def get_accepted_events() -> list[AcceptedEvent]:
    return list(getattr(_tls, "accepted_events", []) or [])


def evidence_context_is_clean() -> bool:
    """Observe cleanup without mutating TLS (used by a real subprocess probe)."""
    return (
        not (getattr(_tls, "rejection_events", None) or [])
        and not (getattr(_tls, "accepted_events", None) or [])
        and not (getattr(_tls, "artifact_receipts", None) or [])
        and getattr(_tls, "case_input", None) is None
        and getattr(_tls, "actual_nodeid", None) is None
        and getattr(_tls, "actual_case_id", None) is None
        and getattr(_tls, "limit_binding", None) is None
        and getattr(_tls, "ledger_row", None) is None
        and getattr(_tls, "declared", None) is None
        and source_artifact_service._source_limits_override is None
    )


def make_synthetic_rejection_event(**kwargs: Any) -> RejectionEvent:
    """Test-only factory — does not mark runtime completion."""
    return RejectionEvent(**kwargs)


def make_synthetic_accepted_event(**kwargs: Any) -> AcceptedEvent:
    return AcceptedEvent(**kwargs)


def _assert_active_case_evidence(res: Any) -> tuple[CaseInput, str, str, dict[str, Any]]:
    case = get_case_input()
    assert case is not None, "CaseInput must build the artifact and configure limits"
    binding = getattr(_tls, "limit_binding", None)
    assert binding is not None, "source_case_limits() must configure the actual HTTP path"
    assert binding.case is case, "artifact and limit configuration used different CaseInput objects"
    assert source_artifact_service._source_limits_override is binding.limits, (
        "actual source service is not using the CaseInput-bound limits object"
    )
    assert getattr(binding.limits, case.bound) == binding.limit_value
    receipts = [
        receipt
        for receipt in (getattr(_tls, "artifact_receipts", None) or [])
        if receipt.case is case and receipt.reachability == case.reachability
    ]
    assert receipts, "CaseInput did not drive the artifact branch"
    request = getattr(res, "request", None)
    try:
        request_content = request.content
    except Exception as exc:  # pragma: no cover - fail-closed diagnostic
        raise AssertionError("HTTP response does not expose its consumed request bytes") from exc
    assert isinstance(request_content, bytes), "consumed HTTP request bytes are unavailable"
    assert any(receipt.payload in request_content for receipt in receipts), (
        "HTTP request did not contain an artifact built by the active CaseInput"
    )
    nodeid = getattr(_tls, "actual_nodeid", None)
    runtime_case_id = getattr(_tls, "actual_case_id", None)
    declared = getattr(_tls, "declared", None)
    assert nodeid, "actual_nodeid not bound"
    assert runtime_case_id, "pytest runtime case id not bound"
    assert declared is not None, "ledger row not bound"
    return case, nodeid, runtime_case_id, declared


# ---------------------------------------------------------------------------
# Mapper field sets (preserved from prior correctives)
# ---------------------------------------------------------------------------


def persisted_column_keys(model: type) -> tuple[str, ...]:
    return tuple(sorted(c.key for c in sa_inspect(model).mapper.column_attrs))


ARTIFACT_FIELDS = persisted_column_keys(ImportSourceArtifact)
BATCH_FIELDS = persisted_column_keys(ProjectAssetImportBatch)
STAGING_FIELDS = persisted_column_keys(ProjectAssetImportStagingRow)
LINE_FIELDS = persisted_column_keys(ProjectAssetLine)
AUDIT_FIELDS = persisted_column_keys(AuditEvent)

_MODEL_FIELDS = {
    ImportSourceArtifact: ARTIFACT_FIELDS,
    ProjectAssetImportBatch: BATCH_FIELDS,
    ProjectAssetImportStagingRow: STAGING_FIELDS,
    ProjectAssetLine: LINE_FIELDS,
    AuditEvent: AUDIT_FIELDS,
}


def assert_field_sets_match_mappers() -> None:
    for model, fields in _MODEL_FIELDS.items():
        live = set(persisted_column_keys(model))
        guarded = set(fields)
        assert guarded == live, f"{model.__name__}: {guarded ^ live}"


def _sort_key(item: Any) -> str:
    return repr(item)


def canonical(value: Any) -> Any:
    if value is None:
        return ("none", None)
    if isinstance(value, Enum):
        et = type(value)
        return ("enum", et.__module__, et.__qualname__, canonical(value.value))
    if isinstance(value, bool):
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
                key=_sort_key,
            )
        )
        return ("dict", items)
    if isinstance(value, list):
        return ("list", tuple(canonical(v) for v in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(canonical(v) for v in value))
    if isinstance(value, set):
        return ("set", tuple(sorted((canonical(v) for v in value), key=_sort_key)))
    raise TypeError(f"unsupported snapshot value type: {type(value)!r}")


def assert_canonical_distinguishes_collisions() -> None:
    from enum import IntEnum

    from app.modules.project_master_data.models import (
        AssetLineReviewStatus,
        ImportBatchStatus,
    )

    assert canonical(1) != canonical(1.0)
    assert canonical(ImportBatchStatus.CREATED) != canonical("created")
    assert canonical(AssetLineReviewStatus.PENDING) != canonical("pending")

    class LocalInt(IntEnum):
        ONE = 1

    assert canonical(LocalInt.ONE) != canonical(1)
    assert canonical({1: "x"}) != canonical({"1": "x"})
    try:
        canonical(object())
        raise AssertionError("expected TypeError")
    except TypeError:
        pass


_COLLECT_SLASH = re.compile(r"(?m)^(\d+)/(\d+) tests? collected\b")
_COLLECT_PLAIN = re.compile(r"(?m)^(\d+) tests? collected\b")


def parse_pytest_collect_selected_count(output: str) -> int:
    m = _COLLECT_SLASH.search(output)
    if m:
        return int(m.group(1))
    m = _COLLECT_PLAIN.search(output)
    if m:
        return int(m.group(1))
    raise ValueError(f"no pytest collect summary found:\n{output[-500:]}")


def assert_pytest_collect_count_exactly(output: str, *, expected: int, returncode: int) -> int:
    if returncode != 0:
        raise AssertionError(f"collect returncode={returncode}:\n{output[-800:]}")
    try:
        n = parse_pytest_collect_selected_count(output)
    except ValueError as e:
        raise AssertionError(str(e)) from e
    if n != expected:
        raise AssertionError(f"expected collect count {expected}, got {n}")
    return n


def _row(model_obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    out = {name: canonical(getattr(model_obj, name)) for name in fields}
    assert set(out.keys()) == set(fields)
    return out


def _as_uuid(value: Any):
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def snapshot_source_intake_preserve(
    db: Session, fake_storage, *, project_id, batch_id
) -> dict[str, Any]:
    assert_field_sets_match_mappers()
    db.expire_all()
    pid, bid = _as_uuid(project_id), _as_uuid(batch_id)
    arts = (
        db.query(ImportSourceArtifact)
        .order_by(ImportSourceArtifact.generation.asc(), ImportSourceArtifact.id.asc())
        .all()
    )
    batches = db.query(ProjectAssetImportBatch).filter(ProjectAssetImportBatch.id == bid).all()
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
    return {
        "objects": {k: bytes(v) for k, v in fake_storage._objects.items()},
        "content_types": dict(fake_storage._content_types),
        "artifacts": [_row(a, ARTIFACT_FIELDS) for a in arts],
        "batches": [_row(b, BATCH_FIELDS) for b in batches],
        "staging": [_row(s, STAGING_FIELDS) for s in staging],
        "lines": [_row(ln, LINE_FIELDS) for ln in lines],
        "audits": [_row(a, AUDIT_FIELDS) for a in audits],
        "project_id": str(pid) if pid else None,
        "batch_id": str(bid) if bid else None,
    }


def assert_source_intake_preserve(db: Session, fake_storage, snap: dict[str, Any]) -> None:
    db.expire_all()
    after = snapshot_source_intake_preserve(
        db, fake_storage, project_id=snap["project_id"], batch_id=snap["batch_id"]
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
    """Reject path: assert vs HTTP, full preserve, then record C from the response."""
    assert res.status_code == status, res.text
    body = res.json()
    detail = body.get("detail")
    assert isinstance(detail, dict), f"detail must be mapping: {detail!r}"
    assert detail.get("error_code") == error_code, detail
    assert_source_intake_preserve(db, fake_storage, snap)

    # C: re-read from response (not echo of arguments alone — use parsed body)
    observed_status = int(res.status_code)
    observed_error = detail.get("error_code")
    assert observed_error == error_code

    case, nodeid, runtime_case_id, declared = _assert_active_case_evidence(res)
    events = getattr(_tls, "rejection_events", None)
    assert events is not None, "evidence context not initialized"
    events.append(
        RejectionEvent(
            actual_nodeid=nodeid,
            actual_case_id=runtime_case_id,
            actual_reachability=case.reachability,
            actual_bound=case.bound,
            declared_reachability=declared["reachability"],
            declared_bound=declared["bound"],
            observed_status=observed_status,
            observed_error_code=str(observed_error),
            row_id=declared["row_id"],
        )
    )


def assert_accepted_source_upload(res, *, status: int = 201) -> None:
    """Accept path: assert real response status, record accepted observation from C."""
    assert res.status_code == status, getattr(res, "text", res)
    observed = int(res.status_code)
    _case, nodeid, runtime_case_id, declared = _assert_active_case_evidence(res)
    events = getattr(_tls, "accepted_events", None)
    assert events is not None, "evidence context not initialized"
    events.append(
        AcceptedEvent(
            row_id=declared["row_id"],
            actual_nodeid=nodeid,
            actual_case_id=runtime_case_id,
            observed_accepted_status=observed,
        )
    )


# Back-compat aliases used by older suites (twelfth/thirteenth)
def reset_strong_helper_context(*_a, **_k) -> None:
    clear_evidence_context()


def get_strong_helper_completed_calls() -> int:
    return len(get_rejection_events())


def get_strong_helper_events():
    """Legacy name — returns rejection events as opaque list."""
    return get_rejection_events()


def reset_strong_helper_calls() -> None:
    clear_evidence_context()


def record_accepted_companion() -> None:
    """Legacy no-op path: accepted recording is via assert_accepted_source_upload."""
    pass


def accepted_companion_recorded() -> bool:
    return len(get_accepted_events()) > 0


def assert_audit_snapshot_detects_mutations() -> None:
    assert_canonical_distinguishes_collisions()
