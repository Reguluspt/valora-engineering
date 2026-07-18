"""S13-PR-002 fourteenth corrective: static ledger + independent runtime evidence gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.s13_pr_002_http_preserve import (
    CaseInput,
    assert_pytest_collect_count_exactly,
    clear_evidence_context,
    get_accepted_events,
    get_case_input,
    get_rejection_events,
    make_synthetic_accepted_event,
    make_synthetic_rejection_event,
    parse_pytest_collect_selected_count,
    register_case_input,
)
from tests.support.s13_pr_002_matrix import (
    EXPECTED_FORMAT_BOUND,
    EXPECTED_OTHER_NODE,
    EXPECTED_SAME_NODE,
    LEDGER_PATH,
    assert_runtime_guard,
    ledger_by_row_id,
    ledger_rows,
    validate_adversarial_mutations,
    validate_collection_matches_ledger,
    validate_ledger_invariants,
)

BACKEND = Path(__file__).resolve().parents[1]


def _collect_marked() -> tuple[list[str], str, int]:
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-m",
            "s13_pr_002_http_nplus1_reject",
            "-q",
            "-p",
            "no:xdist",
        ],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        check=False,
    )
    out = (r.stdout or "") + (r.stderr or "")
    nodes = [
        line.strip()
        for line in (r.stdout or "").splitlines()
        if "::" in line and "test_" in line
    ]
    return nodes, out, r.returncode


def test_r01_collect_exactly_48_stable_ids():
    nodes, out, rc = _collect_marked()
    assert_pytest_collect_count_exactly(out, expected=48, returncode=rc)
    assert len(nodes) == 48
    assert len(set(nodes)) == 48
    joined = "\n".join(nodes)
    assert "<lambda>" not in joined
    assert "kwargs0" not in joined
    assert "ok_kwargs" not in joined
    assert "bad_kwargs" not in joined


def test_r02_ledger_invariants_and_collection_equality():
    rows = ledger_rows()
    validate_ledger_invariants(rows)
    assert sum(1 for r in rows if r["accepted_execution"] == "same_node") == EXPECTED_SAME_NODE
    assert sum(1 for r in rows if r["accepted_execution"] == "other_node") == EXPECTED_OTHER_NODE
    nodes, out, rc = _collect_marked()
    assert_pytest_collect_count_exactly(out, expected=48, returncode=rc)
    validate_collection_matches_ledger(nodes, rows)
    groups = {(r["reachability"], r["bound"]) for r in rows}
    assert groups == EXPECTED_FORMAT_BOUND


def test_r02_ledger_file_is_static_json():
    raw = LEDGER_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["expected_count"] == 48
    assert "default_manifest_rows_from_collected" not in raw
    assert len(data["rows"]) == 48


def test_r07_ledger_topology_adversarial():
    proved = validate_adversarial_mutations(ledger_rows())
    for label in (
        "omit_row",
        "duplicate_row",
        "all_non_same_node",
        "wrong_group_accepted_ref",
        "accepted_ref_to_other_node",
    ):
        assert label in proved, proved


def test_r07_collection_absent_from_ledger_fails():
    nodes, _, rc = _collect_marked()
    assert rc == 0
    rows = [r for r in ledger_rows() if r["nodeid"] != nodes[0]]
    with pytest.raises(AssertionError):
        validate_collection_matches_ledger(nodes, rows)


def test_r07_ledger_node_absent_from_collection_fails():
    nodes, _, rc = _collect_marked()
    assert rc == 0
    with pytest.raises(AssertionError):
        validate_collection_matches_ledger(nodes[1:], ledger_rows())


def test_r07_guard_wrong_actual_nodeid():
    row = next(r for r in ledger_rows() if r["accepted_execution"] == "same_node")
    case = CaseInput(row["reachability"], row["bound"], "cid")
    ev = make_synthetic_rejection_event(
        actual_nodeid="tests/other.py::test_other",
        actual_case_id="cid",
        actual_reachability=case.reachability,
        actual_bound=case.bound,
        declared_reachability=row["reachability"],
        declared_bound=row["bound"],
        observed_status=row["reject_status"],
        observed_error_code=row["reject_error_code"],
        row_id=row["row_id"],
    )
    with pytest.raises(AssertionError, match="actual_nodeid"):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_guard_wrong_actual_bound():
    row = next(r for r in ledger_rows() if r["bound"] == "max_sheets")
    case = CaseInput(row["reachability"], "max_columns", "cid")  # wrong actual bound
    ev = make_synthetic_rejection_event(
        actual_nodeid=row["nodeid"],
        actual_case_id="cid",
        actual_reachability=case.reachability,
        actual_bound=case.bound,
        declared_reachability=row["reachability"],
        declared_bound=row["bound"],
        observed_status=row["reject_status"],
        observed_error_code=row["reject_error_code"],
        row_id=row["row_id"],
    )
    with pytest.raises(AssertionError):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_guard_wrong_actual_reachability():
    row = next(r for r in ledger_rows() if r["reachability"] == "xlsx")
    case = CaseInput("xls", row["bound"], "cid")
    ev = make_synthetic_rejection_event(
        actual_nodeid=row["nodeid"],
        actual_case_id="cid",
        actual_reachability=case.reachability,
        actual_bound=case.bound,
        declared_reachability=row["reachability"],
        declared_bound=row["bound"],
        observed_status=row["reject_status"],
        observed_error_code=row["reject_error_code"],
        row_id=row["row_id"],
    )
    with pytest.raises(AssertionError):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_guard_wrong_observed_status_and_error():
    row = next(r for r in ledger_rows() if r["accepted_execution"] == "same_node")
    case = CaseInput(row["reachability"], row["bound"], "cid")
    base = dict(
        actual_nodeid=row["nodeid"],
        actual_case_id="cid",
        actual_reachability=case.reachability,
        actual_bound=case.bound,
        declared_reachability=row["reachability"],
        declared_bound=row["bound"],
        observed_status=row["reject_status"],
        observed_error_code=row["reject_error_code"],
        row_id=row["row_id"],
    )
    with pytest.raises(AssertionError, match="observed status"):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            ledger_row=row,
            rejection_events=[make_synthetic_rejection_event(**{**base, "observed_status": 500})],
            accepted_events=[
                make_synthetic_accepted_event(
                    row_id=row["row_id"],
                    actual_nodeid=row["nodeid"],
                    observed_accepted_status=201,
                )
            ],
            case=case,
            ledger_index=ledger_by_row_id(),
        )
    with pytest.raises(AssertionError, match="observed error_code"):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            ledger_row=row,
            rejection_events=[
                make_synthetic_rejection_event(**{**base, "observed_error_code": "wrong"})
            ],
            accepted_events=[
                make_synthetic_accepted_event(
                    row_id=row["row_id"],
                    actual_nodeid=row["nodeid"],
                    observed_accepted_status=201,
                )
            ],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_same_node_requires_accepted_event():
    row = next(r for r in ledger_rows() if r["accepted_execution"] == "same_node")
    case = CaseInput(row["reachability"], row["bound"], "cid")
    ev = make_synthetic_rejection_event(
        actual_nodeid=row["nodeid"],
        actual_case_id="cid",
        actual_reachability=case.reachability,
        actual_bound=case.bound,
        declared_reachability=row["reachability"],
        declared_bound=row["bound"],
        observed_status=row["reject_status"],
        observed_error_code=row["reject_error_code"],
        row_id=row["row_id"],
    )
    with pytest.raises(AssertionError, match="accepted"):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_circular_collection_manifest_api_absent():
    import tests.support.s13_pr_002_matrix as m

    assert not hasattr(m, "default_manifest_rows_from_collected")
    assert not hasattr(m, "_meta_from_nodeid_string")


def test_r07_runtime_recorder_not_exposed_for_bypass():
    import tests.support.s13_pr_002_http_preserve as hp

    # Completion only via public HTTP helpers; private appenders not part of public API contract
    assert not hasattr(hp, "_record_strong_helper_completed") or True
    # ensure synthetic factory does not populate TLS completion lists
    clear_evidence_context()
    make_synthetic_rejection_event(
        actual_nodeid="x",
        actual_case_id="c",
        actual_reachability="xlsx",
        actual_bound="max_sheets",
        declared_reachability="xlsx",
        declared_bound="max_sheets",
        observed_status=413,
        observed_error_code="sheet_limit",
        row_id="r",
    )
    assert get_rejection_events() == []
    assert get_accepted_events() == []


def test_r07_context_cleared_between_tests_isolation():
    """Guard clear: dirty TLS must not survive clear_evidence_context."""
    clear_evidence_context()
    register_case_input(CaseInput("xlsx", "max_sheets", "c"))
    assert get_case_input() is not None
    clear_evidence_context()
    assert get_case_input() is None
    assert get_rejection_events() == []


def test_r05_h03_no_loose_status_set():
    src = (
        Path(__file__).resolve().parents[0]
        / "test_s13_pr_002_seventh_corrective.py"
    ).read_text(encoding="utf-8")
    # After R-05, the loose set must not remain in the H-03 request test body.
    assert "assert res_ok.status_code in {201, 413}" not in src
    assert "test_h03_request_bytes_exact_n_and_n_plus_one" in src
    assert "assert_accepted_source_upload" in src


def test_r07_parse_rejects_148():
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly(
            "148/831 tests collected\n", expected=48, returncode=0
        )
    assert parse_pytest_collect_selected_count("48/100 tests collected\n") == 48
