"""Static ledger load + pure validation for S13-PR-002 evidence gate (R-02/R-07)."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from tests.support.s13_pr_002_http_preserve import (
    AcceptedEvent,
    CaseInput,
    RejectionEvent,
    get_case_input,
)

LEDGER_PATH = Path(__file__).resolve().parents[1] / "data" / "s13_pr_002_http_nplus1_ledger.json"

EXPECTED_HTTP_NPLUS1_COUNT = 48
EXPECTED_SAME_NODE = 23
EXPECTED_OTHER_NODE = 25
EXPECTED_FORMAT_BOUND: frozenset[tuple[str, str]] = frozenset(
    {
        ("intake", "max_request_bytes"),
        ("intake", "max_upload_bytes"),
        ("xlsx", "max_sheets"),
        ("xlsx", "max_physical_rows"),
        ("xlsx", "max_columns"),
        ("xlsx", "max_cell_chars"),
        ("xlsx", "max_row_chars"),
        ("xlsx", "max_total_cells"),
        ("xlsx", "max_merged_regions"),
        ("xlsx", "max_merged_regions_per_sheet"),
        ("xlsx", "max_zip_entries"),
        ("xlsx", "max_uncompressed_zip_bytes"),
        ("xls", "max_sheets"),
        ("xls", "max_physical_rows"),
        ("xls", "max_columns"),
        ("xls", "max_cell_chars"),
        ("xls", "max_row_chars"),
        ("xls", "max_total_cells"),
        ("xls", "max_merged_regions"),
        ("xls", "max_merged_regions_per_sheet"),
    }
)


def load_ledger(path: Path | None = None) -> dict[str, Any]:
    p = path or LEDGER_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("expected_count") == EXPECTED_HTTP_NPLUS1_COUNT
    return data


def ledger_rows(path: Path | None = None) -> list[dict[str, Any]]:
    return list(load_ledger(path)["rows"])


def ledger_by_nodeid(path: Path | None = None) -> dict[str, dict[str, Any]]:
    return {r["nodeid"]: r for r in ledger_rows(path)}


def ledger_by_row_id(path: Path | None = None) -> dict[str, dict[str, Any]]:
    return {r["row_id"]: r for r in ledger_rows(path)}


def validate_ledger_invariants(rows: Sequence[dict[str, Any]]) -> None:
    if len(rows) != EXPECTED_HTTP_NPLUS1_COUNT:
        raise AssertionError(f"ledger rows {len(rows)} != {EXPECTED_HTTP_NPLUS1_COUNT}")
    row_ids = [r["row_id"] for r in rows]
    nodeids = [r["nodeid"] for r in rows]
    if len(set(row_ids)) != len(row_ids):
        raise AssertionError("duplicate row_id")
    if len(set(nodeids)) != len(nodeids):
        raise AssertionError("duplicate nodeid")
    same = [r for r in rows if r["accepted_execution"] == "same_node"]
    other = [r for r in rows if r["accepted_execution"] == "other_node"]
    none = [r for r in rows if r["accepted_execution"] not in {"same_node", "other_node"}]
    if none:
        raise AssertionError(f"forbidden accepted_execution values: {none}")
    if len(same) != EXPECTED_SAME_NODE:
        raise AssertionError(f"same_node count {len(same)} != {EXPECTED_SAME_NODE}")
    if len(other) != EXPECTED_OTHER_NODE:
        raise AssertionError(f"other_node count {len(other)} != {EXPECTED_OTHER_NODE}")
    by_id = {r["row_id"]: r for r in rows}
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["reachability"], r["bound"])].append(r)
        if r["accepted_status"] != 201:
            raise AssertionError(f"accepted_status must be 201: {r['row_id']}")
        if r["accepted_execution"] == "same_node":
            if r["accepted_evidence_row_id"] != r["row_id"]:
                raise AssertionError(f"same_node must self-ref: {r['row_id']}")
        else:
            ev = by_id.get(r["accepted_evidence_row_id"])
            if ev is None:
                raise AssertionError(f"missing evidence row {r['accepted_evidence_row_id']}")
            if ev["accepted_execution"] != "same_node":
                raise AssertionError(f"evidence not same_node: {ev['row_id']}")
            if (ev["reachability"], ev["bound"]) != (r["reachability"], r["bound"]):
                raise AssertionError(
                    f"evidence group mismatch {r['row_id']} -> {ev['row_id']}"
                )
    if set(groups.keys()) != EXPECTED_FORMAT_BOUND:
        raise AssertionError(
            f"format/bound mismatch missing={EXPECTED_FORMAT_BOUND - set(groups)} "
            f"extra={set(groups) - EXPECTED_FORMAT_BOUND}"
        )
    for key, items in groups.items():
        if not any(i["accepted_execution"] == "same_node" for i in items):
            raise AssertionError(f"group {key} has no same_node row")


def validate_collection_matches_ledger(
    collected_nodeids: Sequence[str],
    rows: Sequence[dict[str, Any]] | None = None,
) -> None:
    rows = list(rows if rows is not None else ledger_rows())
    validate_ledger_invariants(rows)
    ledger_ids = {r["nodeid"] for r in rows}
    coll = set(collected_nodeids)
    if len(collected_nodeids) != EXPECTED_HTTP_NPLUS1_COUNT:
        raise AssertionError(f"collected {len(collected_nodeids)} != 48")
    if coll != ledger_ids:
        raise AssertionError(
            f"nodeid set mismatch only_collected={sorted(coll - ledger_ids)[:5]} "
            f"only_ledger={sorted(ledger_ids - coll)[:5]}"
        )


def case_input_from_request(request) -> CaseInput:
    """Build B from callspec when parametrized; non-param must register explicitly."""
    nodeid = request.node.nodeid
    callspec = getattr(request.node, "callspec", None)
    if callspec is not None and "limit_field" in callspec.params:
        bound = str(callspec.params["limit_field"])
        # reachability from test module identity in nodeid path + function tokens
        # NOT heuristic on xlsx_extra substring: use explicit path segments
        func = nodeid.split("::")[-1].split("[", 1)[0]
        if "request_bytes" in func or "upload_bytes" in func or "upload_too_large" in func:
            reach = "intake"
        elif "endpoint_xls_" in func or func.endswith("_xls_adapter_limits") or "xls_extra" in func:
            # After xlsx check: function names use endpoint_xls_ or xls_extra (not xlsx)
            if "xlsx" in func:
                reach = "xlsx"
            else:
                reach = "xls"
        elif "xlsx" in func or "cell_limit" in func or "endpoint_cell" in func:
            reach = "xlsx"
        else:
            reach = "xlsx"
        # Fix: j03/i03 use xlsx_extra / xls_extra carefully
        if "xlsx" in func:
            reach = "xlsx"
        elif "_xls_" in func or "xls_adapter" in func or "xls_extra" in func or "endpoint_xls" in func:
            reach = "xls"
        case_id = f"{func}::{bound}"
        return CaseInput(reachability=reach, bound=bound, case_id=case_id)
    # non-param: must already be registered during test body before helper
    existing = get_case_input()
    if existing is None:
        raise AssertionError(
            f"{nodeid}: non-parametrized marked test must call register_case_input() "
            "with the same bound used to configure limits/payload"
        )
    return existing


def assert_runtime_guard(
    *,
    actual_nodeid: str,
    ledger_row: dict[str, Any],
    rejection_events: Sequence[RejectionEvent],
    accepted_events: Sequence[AcceptedEvent],
    case: CaseInput,
    ledger_index: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Compare A (ledger) / B (case) / C (events) for one marked node."""
    if len(rejection_events) != 1:
        raise AssertionError(
            f"{actual_nodeid}: expected 1 rejection event, got {len(rejection_events)}"
        )
    ev = rejection_events[0]
    if ev.actual_nodeid != actual_nodeid:
        raise AssertionError(f"actual_nodeid {ev.actual_nodeid!r} != {actual_nodeid!r}")
    if ev.actual_nodeid != ledger_row["nodeid"]:
        raise AssertionError("event nodeid != ledger nodeid")
    if case.reachability != ledger_row["reachability"] or case.bound != ledger_row["bound"]:
        raise AssertionError(
            f"case B {(case.reachability, case.bound)} != ledger "
            f"{(ledger_row['reachability'], ledger_row['bound'])}"
        )
    if ev.actual_reachability != case.reachability or ev.actual_bound != case.bound:
        raise AssertionError("event actual_* != registered case input B")
    if ev.declared_reachability != ledger_row["reachability"] or ev.declared_bound != ledger_row["bound"]:
        raise AssertionError("declared_* on event != ledger A")
    if ev.observed_status != ledger_row["reject_status"]:
        raise AssertionError(
            f"observed status {ev.observed_status} != ledger {ledger_row['reject_status']}"
        )
    if ev.observed_error_code != ledger_row["reject_error_code"]:
        raise AssertionError(
            f"observed error_code {ev.observed_error_code!r} != "
            f"ledger {ledger_row['reject_error_code']!r}"
        )
    if ev.row_id != ledger_row["row_id"]:
        raise AssertionError("row_id mismatch")

    if ledger_row["accepted_execution"] == "same_node":
        if len(accepted_events) != 1:
            raise AssertionError(
                f"{actual_nodeid}: same_node requires 1 accepted event, got {len(accepted_events)}"
            )
        ae = accepted_events[0]
        if ae.observed_accepted_status != ledger_row["accepted_status"]:
            raise AssertionError(
                f"accepted status {ae.observed_accepted_status} != {ledger_row['accepted_status']}"
            )
        if ae.row_id != ledger_row["row_id"] or ae.actual_nodeid != actual_nodeid:
            raise AssertionError("accepted event identity mismatch")
    else:
        # other_node: static reference only (no accepted event required in isolation)
        idx = ledger_index or ledger_by_row_id()
        ev_row = idx.get(ledger_row["accepted_evidence_row_id"])
        if ev_row is None or ev_row["accepted_execution"] != "same_node":
            raise AssertionError("other_node evidence row invalid")
        if (ev_row["reachability"], ev_row["bound"]) != (
            ledger_row["reachability"],
            ledger_row["bound"],
        ):
            raise AssertionError("other_node evidence group mismatch")
        # accepted_events may be empty for reject-only other_node
        if accepted_events:
            raise AssertionError("other_node should not record same-node accept on this test")


def validate_adversarial_mutations(base_rows: list[dict[str, Any]]) -> list[str]:
    """Pure ledger topology adversarial checks (isolated copies)."""
    proved: list[str] = []

    def fail(label: str, rows: list[dict]):
        try:
            validate_ledger_invariants(rows)
        except AssertionError:
            proved.append(label)
            return
        raise AssertionError(f"{label} unexpectedly passed")

    # omit one row
    fail("omit_row", base_rows[1:])

    # duplicate row
    fail("duplicate_row", base_rows + [base_rows[0]])

    # all non-same-node
    bad = []
    for r in base_rows:
        rr = dict(r)
        if rr["accepted_execution"] == "same_node":
            # point to another same if any, else break topology
            rr["accepted_execution"] = "other_node"
            rr["accepted_evidence_row_id"] = "DOES_NOT_EXIST"
        bad.append(rr)
    fail("all_non_same_node", bad)

    # wrong-group accepted reference
    same = [r for r in base_rows if r["accepted_execution"] == "same_node"]
    other = [r for r in base_rows if r["accepted_execution"] == "other_node"]
    if same and other:
        bad = [dict(r) for r in base_rows]
        for i, r in enumerate(bad):
            if r["row_id"] == other[0]["row_id"]:
                # point to same_node of different group
                target = next(
                    s
                    for s in same
                    if (s["reachability"], s["bound"])
                    != (r["reachability"], r["bound"])
                )
                bad[i] = dict(r, accepted_evidence_row_id=target["row_id"])
                break
        fail("wrong_group_accepted_ref", bad)

    # evidence points to other_node
    if same and other:
        bad = [dict(r) for r in base_rows]
        for i, r in enumerate(bad):
            if r["row_id"] == other[0]["row_id"]:
                bad[i] = dict(r, accepted_evidence_row_id=other[1]["row_id"] if len(other) > 1 else other[0]["row_id"])
                # force evidence to be an other_node row
                if bad[i]["accepted_evidence_row_id"] == r["row_id"]:
                    bad[i]["accepted_evidence_row_id"] = other[-1]["row_id"]
                break
        fail("accepted_ref_to_other_node", bad)

    return proved
