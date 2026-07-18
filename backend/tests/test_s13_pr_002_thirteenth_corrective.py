"""S13-PR-002 thirteenth corrective: N-01…N-04 anti-vacuity evidence.

Closes independent re-audit F-01…F-03 at tip 7334126:
- Enum-first typed canonicalization
- runtime events bound to node/status/error/reachability/bound
- non-vacuous manifest validation with adversarial negatives
- exact-48 collect parser (rejects 148 / subprocess failure)
"""
from __future__ import annotations

import subprocess
import sys
from enum import Enum, IntEnum
from pathlib import Path

import pytest

from app.modules.project_master_data.models import (
    AssetLineReviewStatus,
    ImportBatchStatus,
)
from tests.support.s13_pr_002_http_preserve import (
    assert_canonical_distinguishes_collisions,
    assert_pytest_collect_count_exactly,
    canonical,
    parse_pytest_collect_selected_count,
    StrongHelperEvent,
    StrongHelperExpectation,
    accepted_companion_recorded,
    get_strong_helper_events,
    record_accepted_companion,
    reset_strong_helper_context,
    _record_strong_helper_completed,
)
from tests.support.s13_pr_002_matrix import (
    EXPECTED_FORMAT_BOUND,
    EXPECTED_HTTP_NPLUS1_COUNT,
    assert_event_matches_expectation,
    default_manifest_rows_from_collected,
    validate_manifest_adversarial_cases,
    validate_matrix,
    _meta_from_nodeid_string,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _collect_marked_nodeids() -> tuple[list[str], str, int]:
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-m",
            "s13_pr_002_http_nplus1_reject",
            "-q",
        ],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    out = (r.stdout or "") + (r.stderr or "")
    nodeids = [
        line.strip()
        for line in (r.stdout or "").splitlines()
        if "::" in line and "test_" in line and not line.strip().startswith("=")
    ]
    return nodeids, out, r.returncode


# ---------------------------------------------------------------------------
# N-01
# ---------------------------------------------------------------------------


def test_n01_canonical_enum_before_scalar_bases():
    assert_canonical_distinguishes_collisions()


def test_n01_project_string_enums_vs_scalars():
    assert canonical(ImportBatchStatus.CREATED) != canonical("created")
    assert canonical(AssetLineReviewStatus.PENDING) != canonical("pending")
    # Enum class identity is part of the form
    a = canonical(ImportBatchStatus.CREATED)
    assert a[0] == "enum"
    assert a[1].endswith("project_master_data.models")
    assert a[2] == "ImportBatchStatus"


def test_n01_intenum_vs_int():
    class LocalInt(IntEnum):
        ONE = 1

    assert canonical(LocalInt.ONE) != canonical(1)


def test_n01_two_enum_classes_same_value():
    class OtherCreated(str, Enum):
        CREATED = "created"

    assert canonical(ImportBatchStatus.CREATED) != canonical(OtherCreated.CREATED)


def test_n01_typed_dict_keys_and_stable_order():
    import uuid

    u = uuid.UUID(int=9)
    assert canonical({1: "x"}) != canonical({"1": "x"})
    assert canonical({u: "x"}) != canonical({str(u): "x"})
    assert canonical({"z": 1, "a": 2}) == canonical({"a": 2, "z": 1})


def test_n01_unsupported_type_fail_closed():
    with pytest.raises(TypeError):
        canonical(object())


# ---------------------------------------------------------------------------
# N-04 exact collect count
# ---------------------------------------------------------------------------


def test_n04_parse_collect_count_exact_and_rejects_148():
    assert parse_pytest_collect_selected_count("48/831 tests collected in 0.4s\n") == 48
    assert parse_pytest_collect_selected_count("48 tests collected in 0.1s\n") == 48
    # Must NOT accept 148 as 48
    assert parse_pytest_collect_selected_count("148/831 tests collected in 0.4s\n") == 148
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly(
            "148/831 tests collected in 0.4s\n", expected=48, returncode=0
        )
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly(
            "480/831 tests collected in 0.4s\n", expected=48, returncode=0
        )
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly(
            "no summary here\n", expected=48, returncode=0
        )
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly(
            "48/831 tests collected\n", expected=48, returncode=2
        )


def test_n04_live_collect_count_is_exactly_48():
    nodeids, out, rc = _collect_marked_nodeids()
    n = assert_pytest_collect_count_exactly(
        out, expected=EXPECTED_HTTP_NPLUS1_COUNT, returncode=rc
    )
    assert n == 48
    assert len(nodeids) == 48


# ---------------------------------------------------------------------------
# N-02 / N-03 runtime events + manifest
# ---------------------------------------------------------------------------


def test_n02_event_records_only_after_full_success():
    exp = StrongHelperExpectation(
        nodeid="tests/fake.py::test_fake",
        reachability="xlsx",
        bound="max_sheets",
        error_code="sheet_limit",
        status=413,
        accepted_mode="none",
    )
    reset_strong_helper_context(exp)
    # Simulate completed recording
    _record_strong_helper_completed(status=413, error_code="sheet_limit")
    events = get_strong_helper_events()
    assert len(events) == 1
    assert events[0].nodeid == exp.nodeid
    assert events[0].error_code == "sheet_limit"
    assert events[0].bound == "max_sheets"
    assert events[0].reachability == "xlsx"
    assert events[0].status == 413


def test_n02_event_guard_rejects_wrong_metadata():
    exp = StrongHelperExpectation(
        nodeid="tests/fake.py::test_fake",
        reachability="xlsx",
        bound="max_sheets",
        error_code="sheet_limit",
        status=413,
        accepted_mode="none",
    )
    wrong = [
        StrongHelperEvent(
            nodeid="tests/fake.py::test_fake",
            status=413,
            error_code="deliberately_wrong",
            reachability="xlsx",
            bound="max_sheets",
        )
    ]
    with pytest.raises(AssertionError):
        assert_event_matches_expectation(wrong, exp, accepted_companion=False)

    wrong_node = [
        StrongHelperEvent(
            nodeid="tests/other.py::test_other",
            status=413,
            error_code="sheet_limit",
            reachability="xlsx",
            bound="max_sheets",
        )
    ]
    with pytest.raises(AssertionError):
        assert_event_matches_expectation(wrong_node, exp, accepted_companion=False)

    # same_node requires accepted companion
    exp2 = StrongHelperExpectation(
        nodeid="tests/fake.py::test_fake",
        reachability="intake",
        bound="max_upload_bytes",
        error_code="upload_too_large",
        status=413,
        accepted_mode="same_node",
    )
    ok_ev = [
        StrongHelperEvent(
            nodeid=exp2.nodeid,
            status=413,
            error_code="upload_too_large",
            reachability="intake",
            bound="max_upload_bytes",
        )
    ]
    with pytest.raises(AssertionError):
        assert_event_matches_expectation(ok_ev, exp2, accepted_companion=False)
    assert_event_matches_expectation(ok_ev, exp2, accepted_companion=True)


def test_n03_live_manifest_validates_against_collected_nodes():
    nodeids, out, rc = _collect_marked_nodeids()
    assert_pytest_collect_count_exactly(out, expected=48, returncode=rc)
    rows = default_manifest_rows_from_collected(nodeids)
    validate_matrix(
        collected_nodeids=nodeids,
        manifest_rows=rows,
        expected_format_bound=EXPECTED_FORMAT_BOUND,
        expected_count=48,
    )
    # format/bound set size
    assert {(r.reachability, r.bound) for r in rows} == EXPECTED_FORMAT_BOUND
    assert len(rows) == 20


def test_n03_adversarial_manifest_mutations_fail():
    nodeids, out, rc = _collect_marked_nodeids()
    assert rc == 0
    proved = validate_manifest_adversarial_cases(nodeids)
    required = {
        "wrong_error_code",
        "nonexistent_accepted_function",
        "wrong_reachability",
        "wrong_exact_nodeid",
        "duplicate_format_bound",
        "omitted_marked_node",
    }
    assert required.issubset(set(proved)), proved


def test_n03_every_collected_node_has_resolvable_meta():
    nodeids, out, rc = _collect_marked_nodeids()
    assert rc == 0
    for nid in nodeids:
        meta = _meta_from_nodeid_string(nid)
        assert meta.bound
        assert meta.error_code
        assert meta.reachability in {"intake", "xlsx", "xls"}
        assert meta.status in {400, 413}


def test_n03_threat_not_in_collected_matrix():
    nodeids, out, rc = _collect_marked_nodeids()
    assert rc == 0
    assert all("threat_http" not in n for n in nodeids)


def test_n02_accepted_companion_flag_isolated():
    reset_strong_helper_context(None)
    assert accepted_companion_recorded() is False
    record_accepted_companion()
    assert accepted_companion_recorded() is True
    reset_strong_helper_context(None)
    assert accepted_companion_recorded() is False
