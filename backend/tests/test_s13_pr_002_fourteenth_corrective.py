"""S13-PR-002 fourteenth corrective: static ledger + independent runtime evidence gate."""

from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.support.s13_pr_002_http_preserve import (
    CaseInput,
    assert_pytest_collect_count_exactly,
    clear_evidence_context,
    evidence_context_is_clean,
    get_accepted_events,
    get_case_input,
    get_rejection_events,
    make_synthetic_accepted_event,
    make_synthetic_rejection_event,
    parse_pytest_collect_selected_count,
    register_case_input,
    source_case_limits,
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
        line.strip() for line in (r.stdout or "").splitlines() if "::" in line and "test_" in line
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
    case = CaseInput(row["reachability"], row["bound"])
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
            actual_case_id="cid",
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_guard_wrong_actual_case_id():
    row = next(r for r in ledger_rows() if r["accepted_execution"] == "same_node")
    case = CaseInput(row["reachability"], row["bound"])
    ev = make_synthetic_rejection_event(
        actual_nodeid=row["nodeid"],
        actual_case_id="forged-case-id",
        actual_reachability=case.reachability,
        actual_bound=case.bound,
        declared_reachability=row["reachability"],
        declared_bound=row["bound"],
        observed_status=row["reject_status"],
        observed_error_code=row["reject_error_code"],
        row_id=row["row_id"],
    )
    with pytest.raises(AssertionError, match="actual_case_id"):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            actual_case_id="pytest-runtime-case-id",
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_guard_wrong_actual_bound():
    row = next(
        r
        for r in ledger_rows()
        if r["reachability"] == "xlsx" and r["bound"] == "max_sheets"
    )
    case = CaseInput(row["reachability"], "max_columns")  # wrong actual bound
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
            actual_case_id="cid",
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_guard_wrong_actual_reachability():
    row = next(r for r in ledger_rows() if r["reachability"] == "xlsx")
    case = CaseInput("xls", row["bound"])
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
            actual_case_id="cid",
            ledger_row=row,
            rejection_events=[ev],
            accepted_events=[],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_guard_wrong_observed_status_and_error():
    row = next(r for r in ledger_rows() if r["accepted_execution"] == "same_node")
    case = CaseInput(row["reachability"], row["bound"])
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
            actual_case_id="cid",
            ledger_row=row,
            rejection_events=[make_synthetic_rejection_event(**{**base, "observed_status": 500})],
            accepted_events=[
                make_synthetic_accepted_event(
                    row_id=row["row_id"],
                    actual_nodeid=row["nodeid"],
                    actual_case_id="cid",
                    observed_accepted_status=201,
                )
            ],
            case=case,
            ledger_index=ledger_by_row_id(),
        )
    with pytest.raises(AssertionError, match="observed error_code"):
        assert_runtime_guard(
            actual_nodeid=row["nodeid"],
            actual_case_id="cid",
            ledger_row=row,
            rejection_events=[
                make_synthetic_rejection_event(**{**base, "observed_error_code": "wrong"})
            ],
            accepted_events=[
                make_synthetic_accepted_event(
                    row_id=row["row_id"],
                    actual_nodeid=row["nodeid"],
                    actual_case_id="cid",
                    observed_accepted_status=201,
                )
            ],
            case=case,
            ledger_index=ledger_by_row_id(),
        )


def test_r07_same_node_requires_accepted_event():
    row = next(r for r in ledger_rows() if r["accepted_execution"] == "same_node")
    case = CaseInput(row["reachability"], row["bound"])
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
            actual_case_id="cid",
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

    assert not hasattr(hp, "_append_rejection_event")
    assert not hasattr(hp, "_append_accepted_event")
    tree = ast.parse(inspect.getsource(hp))
    append_owners: dict[str, set[str]] = {
        "RejectionEvent": set(),
        "AcceptedEvent": set(),
    }
    for fn in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
        for call in (node for node in ast.walk(fn) if isinstance(node, ast.Call)):
            if not (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "append"
                and call.args
                and isinstance(call.args[0], ast.Call)
                and isinstance(call.args[0].func, ast.Name)
            ):
                continue
            event_name = call.args[0].func.id
            if event_name in append_owners:
                append_owners[event_name].add(fn.name)
    assert append_owners == {
        "RejectionEvent": {"assert_http_rejection_preserve"},
        "AcceptedEvent": {"assert_accepted_source_upload"},
    }

    # Synthetic factories construct values but cannot mark runtime completion.
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
    register_case_input(CaseInput("xlsx", "max_sheets"))
    assert get_case_input() is not None
    clear_evidence_context()
    assert evidence_context_is_clean()
    assert get_case_input() is None
    assert get_rejection_events() == []


def test_r07_case_input_rejects_consistent_lie_attack():
    """Changing H03's declared bound cannot retain its old max-upload setup."""
    case = CaseInput("intake", "max_upload_bytes")
    case.build_artifact(intake=b"payload")
    with pytest.raises(AssertionError, match="duplicate target bound"):
        with source_case_limits(case, 10, max_upload_bytes=10 * 1024 * 1024):
            pass


def test_r07_case_input_reachability_selects_real_artifact_branch():
    case = CaseInput("xls", "max_sheets")
    with pytest.raises(AssertionError, match="requires only its matching artifact builder"):
        case.build_artifact(xlsx=b"PK-not-an-xls")


def test_r07_active_binding_rejects_unused_artifact_and_replaced_limit_seam():
    import tests.support.s13_pr_002_http_preserve as hp

    row = next(
        r
        for r in ledger_rows()
        if r["reachability"] == "xlsx" and r["bound"] == "max_sheets"
    )
    case = CaseInput(row["reachability"], row["bound"])
    payload = case.build_artifact(xlsx=b"PK-active-artifact")
    hp.set_runtime_identity(row["nodeid"], "runtime-case")
    hp.set_ledger_row(row)
    with source_case_limits(case, 1):
        wrong_request = SimpleNamespace(request=SimpleNamespace(content=b"unrelated"))
        with pytest.raises(AssertionError, match="did not contain an artifact"):
            hp._assert_active_case_evidence(wrong_request)

        hp.source_artifact_service.set_source_limits_override(
            hp.SourceArtifactLimits(max_columns=1)
        )
        right_request = SimpleNamespace(request=SimpleNamespace(content=payload))
        with pytest.raises(AssertionError, match="actual source service"):
            hp._assert_active_case_evidence(right_request)


def test_r07_no_inference_or_direct_limit_seam_in_marked_tests():
    import tests.support.s13_pr_002_matrix as matrix

    conftest_source = (BACKEND / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "_reachability_from_func" not in conftest_source
    assert not hasattr(matrix, "case_input_from_request")

    files = sorted({row["nodeid"].split("::", 1)[0] for row in ledger_rows()})
    marked_functions = 0
    for relative in files:
        tree = ast.parse((BACKEND / relative).read_text(encoding="utf-8"))
        for fn in (node for node in tree.body if isinstance(node, ast.FunctionDef)):
            decorators = {ast.unparse(d) for d in fn.decorator_list}
            if not any("s13_pr_002_http_nplus1_reject" in d for d in decorators):
                continue
            marked_functions += 1
            calls = {
                node.func.id
                for node in ast.walk(fn)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            attrs = {
                node.func.attr
                for node in ast.walk(fn)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            names = {node.id for node in ast.walk(fn) if isinstance(node, ast.Name)}
            forbidden_calls = {
                "set_source_limits_override",
                "SourceArtifactLimits",
                "register_case_input",
                "make_synthetic_rejection_event",
                "make_synthetic_accepted_event",
            }
            assert not ((calls | attrs) & forbidden_calls), fn.name
            assert "_tls" not in names | attrs, fn.name
            assert "RejectionEvent" not in names, fn.name
            assert "AcceptedEvent" not in names, fn.name
            assert "source_case_limits" in calls, fn.name
            assert "build_artifact" in attrs, fn.name
    assert marked_functions == 19


def test_r07_guard_failure_still_cleans_before_next_node(tmp_path):
    """Real fail→clean lifecycle probe across two pytest nodes in one process."""
    target = (
        "tests/test_s13_pr_002_seventh_corrective.py::test_h03_request_bytes_exact_n_and_n_plus_one"
    )
    following = "tests/test_s13_pr_002_fourteenth_corrective.py::test_r07_parse_rejects_148"
    plugin = tmp_path / "s13_cleanup_probe_plugin.py"
    plugin.write_text(
        textwrap.dedent(
            f"""
            import pytest
            import tests.support.s13_pr_002_http_preserve as hp

            TARGET = {target!r}
            FOLLOWING = {following!r}

            @pytest.hookimpl(tryfirst=True)
            def pytest_runtest_teardown(item, nextitem):
                if item.nodeid == TARGET:
                    hp._tls.case_input = hp.CaseInput("intake", "max_upload_bytes")
                    print("S13_PROBE_INJECTED_GUARD_FAILURE")

            @pytest.hookimpl(tryfirst=True)
            def pytest_runtest_setup(item):
                if item.nodeid == FOLLOWING:
                    clean = hp.evidence_context_is_clean()
                    print(f"S13_PROBE_NEXT_NODE_CLEAN={{clean}}")
                    if not clean:
                        raise AssertionError("S13 evidence context leaked after guard failure")
            """
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(tmp_path), env.get("PYTHONPATH", "")) if part
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            target,
            following,
            "-q",
            "-s",
            "-p",
            "no:xdist",
            "-p",
            "s13_cleanup_probe_plugin",
        ],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    output = (result.stdout or "") + (result.stderr or "")
    assert result.returncode != 0, output
    assert "S13_PROBE_INJECTED_GUARD_FAILURE" in output
    assert "S13_PROBE_NEXT_NODE_CLEAN=True" in output
    assert "case B ('intake', 'max_upload_bytes')" in output


def test_r05_h03_no_loose_status_set():
    src = (Path(__file__).resolve().parents[0] / "test_s13_pr_002_seventh_corrective.py").read_text(
        encoding="utf-8"
    )
    # After R-05, the loose set must not remain in the H-03 request test body.
    assert "assert res_ok.status_code in {201, 413}" not in src
    assert "test_h03_request_bytes_exact_n_and_n_plus_one" in src
    assert "assert_accepted_source_upload" in src


def test_r07_parse_rejects_148():
    with pytest.raises(AssertionError):
        assert_pytest_collect_count_exactly("148/831 tests collected\n", expected=48, returncode=0)
    assert parse_pytest_collect_selected_count("48/100 tests collected\n") == 48
