"""Executable HTTP N+1 matrix metadata + non-vacuous validation (N-02/N-03).

Pure functions: no shared mutable suite state. Callers pass collected nodeids
and runtime events explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from tests.support.s13_pr_002_http_preserve import (
    StrongHelperEvent,
    StrongHelperExpectation,
)

EXPECTED_HTTP_NPLUS1_COUNT = 48

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


@dataclass(frozen=True)
class NodeMeta:
    """Declared identity for one marked HTTP N+1 rejection parameter."""

    reachability: str
    bound: str
    error_code: str
    status: int
    accepted_mode: str  # "same_node" | "none"
    # Exact function name of accepted evidence (same function when same_node).
    accepted_function: str


# Non-parametrized function → fixed meta.
_FUNCTION_META: dict[str, NodeMeta] = {
    "test_e04_endpoint_upload_bytes_limit": NodeMeta(
        "intake", "max_upload_bytes", "upload_too_large", 413, "same_node",
        "test_e04_endpoint_upload_bytes_limit",
    ),
    "test_e04_endpoint_cell_limit_preserves_prior": NodeMeta(
        "xlsx", "max_cell_chars", "cell_length_limit", 400, "none",
        "test_e04_endpoint_cell_limit_preserves_prior",
    ),
    "test_endpoint_cell_limit_no_reservation": NodeMeta(
        "xlsx", "max_cell_chars", "cell_length_limit", 400, "none",
        "test_endpoint_cell_limit_no_reservation",
    ),
    "test_g03_endpoint_cell_limit_stable_status": NodeMeta(
        "xlsx", "max_cell_chars", "cell_length_limit", 400, "none",
        "test_g03_endpoint_cell_limit_stable_status",
    ),
    "test_h03_request_bytes_exact_n_and_n_plus_one": NodeMeta(
        "intake", "max_request_bytes", "request_too_large", 413, "none",
        "test_h03_request_bytes_exact_n_and_n_plus_one",
    ),
    "test_h03_upload_bytes_exact_n_and_n_plus_one": NodeMeta(
        "intake", "max_upload_bytes", "upload_too_large", 413, "same_node",
        "test_h03_upload_bytes_exact_n_and_n_plus_one",
    ),
    "test_i03_request_bytes_exact_n_accepted_n_plus_one_rejected": NodeMeta(
        "intake", "max_request_bytes", "request_too_large", 413, "same_node",
        "test_i03_request_bytes_exact_n_accepted_n_plus_one_rejected",
    ),
    "test_i03_upload_bytes_exact_n_accepted_n_plus_one_rejected": NodeMeta(
        "intake", "max_upload_bytes", "upload_too_large", 413, "same_node",
        "test_i03_upload_bytes_exact_n_accepted_n_plus_one_rejected",
    ),
    "test_k03_reject_preserves_objects_content_types_and_all_audits": NodeMeta(
        "xlsx", "max_sheets", "sheet_limit", 413, "none",
        "test_k03_reject_preserves_objects_content_types_and_all_audits",
    ),
    "test_k03_upload_too_large_full_snapshot": NodeMeta(
        "intake", "max_upload_bytes", "upload_too_large", 413, "none",
        "test_k03_upload_too_large_full_snapshot",
    ),
    "test_l03_upload_too_large_full_preserve": NodeMeta(
        "intake", "max_upload_bytes", "upload_too_large", 413, "none",
        "test_l03_upload_too_large_full_preserve",
    ),
}


def _function_name_from_nodeid(nodeid: str) -> str:
    # nodeid: path::test_name[params] or path::test_name
    tail = nodeid.split("::", 1)[-1]
    return tail.split("[", 1)[0]


def _reachability_for_function(func: str) -> str:
    if "request_bytes" in func or "upload_bytes" in func or "upload_too_large" in func:
        return "intake"
    # Check xlsx *before* xls — "xlsx_extra" contains the substring "xls_extra".
    if (
        "_xlsx_" in func
        or "xlsx_adapter" in func
        or "xlsx_extra" in func
        or "endpoint_xlsx" in func
        or func.endswith("_xlsx_adapter_limits")
        or "xlsx_n_plus_one" in func
        or "xlsx_rejects" in func
    ):
        return "xlsx"
    if (
        "_xls_" in func
        or "xls_adapter" in func
        or "xls_extra" in func
        or "endpoint_xls" in func
        or func.endswith("_xls_adapter_limits")
    ):
        return "xls"
    return "xlsx"


def resolve_node_meta(
    nodeid: str,
    *,
    callspec_params: Mapping[str, Any] | None = None,
) -> NodeMeta:
    """Resolve declared metadata for a marked node from function registry + callspec."""
    func = _function_name_from_nodeid(nodeid)
    params = dict(callspec_params or {})

    if params:
        bound = params.get("limit_field")
        error_code = params.get("error_code")
        status = params.get("status", params.get("bad_status"))
        if bound is None or error_code is None or status is None:
            raise KeyError(
                f"parametrized node {nodeid!r} missing limit_field/error_code/status in {params!r}"
            )
        reachability = _reachability_for_function(func)
        # Parametrized matrices that include N-accept companions
        same = func in {
            "test_i03_endpoint_xlsx_adapter_exact_n_and_n_plus_one",
            "test_i03_endpoint_xls_adapter_exact_n_and_n_plus_one",
            "test_j03_endpoint_xlsx_extra_adapter_bounds",
            "test_j03_endpoint_xls_extra_adapter_bounds",
        }
        return NodeMeta(
            reachability=reachability,
            bound=str(bound),
            error_code=str(error_code),
            status=int(status),
            accepted_mode="same_node" if same else "none",
            accepted_function=func,
        )

    if func in _FUNCTION_META:
        return _FUNCTION_META[func]
    raise KeyError(f"no metadata registry entry for marked node {nodeid!r} ({func})")


def expectation_for_request(request) -> StrongHelperExpectation:
    """Build StrongHelperExpectation from a pytest request for a marked node."""
    callspec = getattr(request.node, "callspec", None)
    params = callspec.params if callspec is not None else None
    meta = resolve_node_meta(request.node.nodeid, callspec_params=params)
    return StrongHelperExpectation(
        nodeid=request.node.nodeid,
        reachability=meta.reachability,
        bound=meta.bound,
        error_code=meta.error_code,
        status=meta.status,
        accepted_mode=meta.accepted_mode,
    )


def assert_event_matches_expectation(
    events: Sequence[StrongHelperEvent],
    exp: StrongHelperExpectation,
    *,
    accepted_companion: bool,
) -> None:
    """Autouse post-condition: exactly one matching completed event."""
    if len(events) != 1:
        raise AssertionError(
            f"{exp.nodeid}: expected exactly 1 completed strong-helper event, got {len(events)}"
        )
    ev = events[0]
    if ev.nodeid != exp.nodeid:
        raise AssertionError(
            f"event nodeid {ev.nodeid!r} != expected {exp.nodeid!r}"
        )
    if ev.status != exp.status:
        raise AssertionError(f"event status {ev.status} != expected {exp.status}")
    if ev.error_code != exp.error_code:
        raise AssertionError(
            f"event error_code {ev.error_code!r} != expected {exp.error_code!r}"
        )
    if ev.reachability != exp.reachability:
        raise AssertionError(
            f"event reachability {ev.reachability!r} != expected {exp.reachability!r}"
        )
    if ev.bound != exp.bound:
        raise AssertionError(f"event bound {ev.bound!r} != expected {exp.bound!r}")
    if exp.accepted_mode == "same_node" and not accepted_companion:
        raise AssertionError(
            f"{exp.nodeid}: accepted_mode=same_node but accepted companion was not recorded"
        )


@dataclass(frozen=True)
class ManifestRow:
    reachability: str
    bound: str
    error_code: str
    # Exact collected nodeid OR unique function name for non-param nodes.
    # For multi-node coverage of the same bound, list all representative nodeids
    # that must exist in the collected set and share this error_code.
    rejected_nodeids: tuple[str, ...]
    accepted_function: str
    accepted_mode: str  # "same_node" | "none"


def default_manifest_rows_from_collected(
    collected_nodeids: Sequence[str],
) -> list[ManifestRow]:
    """Build canonical manifest rows from the live collected set.

    Groups by (reachability, bound) using resolve_node_meta. Ensures every
    collected node is represented and every format/bound tuple is covered.
    """
    by_key: dict[tuple[str, str], list[tuple[str, NodeMeta]]] = {}
    for nid in collected_nodeids:
        # callspec not available from nodeid alone for params — parse from nodeid
        meta = _meta_from_nodeid_string(nid)
        key = (meta.reachability, meta.bound)
        by_key.setdefault(key, []).append((nid, meta))

    rows: list[ManifestRow] = []
    for key in sorted(by_key.keys()):
        items = by_key[key]
        # All nodes for a format/bound must share the same error_code
        error_codes = {m.error_code for _, m in items}
        if len(error_codes) != 1:
            raise AssertionError(f"inconsistent error_codes for {key}: {error_codes}")
        error_code = next(iter(error_codes))
        # Prefer same_node if any node has it
        accepted_mode = "same_node" if any(m.accepted_mode == "same_node" for _, m in items) else "none"
        accepted_function = items[0][1].accepted_function
        rows.append(
            ManifestRow(
                reachability=key[0],
                bound=key[1],
                error_code=error_code,
                rejected_nodeids=tuple(sorted(n for n, _ in items)),
                accepted_function=accepted_function,
                accepted_mode=accepted_mode,
            )
        )
    return rows


def _meta_from_nodeid_string(nodeid: str) -> NodeMeta:
    """Derive meta from collected nodeid text (no live callspec).

    Parametrized ids embed limit_field as the first ``-``-separated token and
    end with ``{error_code}-{status}``.
    """
    func = _function_name_from_nodeid(nodeid)
    if "[" not in nodeid.split("::")[-1]:
        return resolve_node_meta(nodeid, callspec_params=None)

    br = nodeid.split("[", 1)[1].rstrip("]")
    parts = br.split("-")
    known_codes = {
        "sheet_limit",
        "physical_row_limit",
        "column_limit",
        "cell_length_limit",
        "row_char_limit",
        "total_cell_limit",
        "merged_region_limit",
        "zip_entry_limit",
        "zip_expansion_limit",
        "request_too_large",
        "upload_too_large",
    }
    error_code = None
    status = None
    for p in parts:
        if p in known_codes:
            error_code = p
        if p.isdigit():
            status = int(p)
    # First token is always the limit_field / bound name (underscores intact).
    bound = parts[0] if parts else None
    if bound is None or error_code is None or status is None:
        raise KeyError(f"cannot parse meta from nodeid {nodeid!r} parts={parts!r}")

    reachability = _reachability_for_function(func)
    same = func in {
        "test_i03_endpoint_xlsx_adapter_exact_n_and_n_plus_one",
        "test_i03_endpoint_xls_adapter_exact_n_and_n_plus_one",
        "test_j03_endpoint_xlsx_extra_adapter_bounds",
        "test_j03_endpoint_xls_extra_adapter_bounds",
    }
    return NodeMeta(
        reachability=reachability,
        bound=bound,
        error_code=error_code,
        status=status,
        accepted_mode="same_node" if same else "none",
        accepted_function=func,
    )


def validate_matrix(
    *,
    collected_nodeids: Sequence[str],
    manifest_rows: Sequence[ManifestRow],
    expected_format_bound: frozenset[tuple[str, str]] = EXPECTED_FORMAT_BOUND,
    expected_count: int = EXPECTED_HTTP_NPLUS1_COUNT,
    runtime_events: Sequence[StrongHelperEvent] | None = None,
    accepted_companion_nodeids: Sequence[str] | None = None,
) -> None:
    """Pure non-vacuous matrix validation.

    Raises AssertionError on any inconsistency (wrong error_code, missing
    accepted function, wrong bound, duplicate incompatible mapping, unmarked
    omission, etc.).
    """
    collected = list(collected_nodeids)
    if len(collected) != expected_count:
        raise AssertionError(
            f"collected count {len(collected)} != expected {expected_count}"
        )
    collected_set = set(collected)
    if len(collected_set) != len(collected):
        raise AssertionError("duplicate collected nodeids")

    # Every collected node has resolvable meta
    node_meta: dict[str, NodeMeta] = {}
    for nid in collected:
        node_meta[nid] = _meta_from_nodeid_string(nid)

    # Manifest unique format/bound
    keys = [(r.reachability, r.bound) for r in manifest_rows]
    if len(keys) != len(set(keys)):
        raise AssertionError(f"duplicate format/bound in manifest: {keys}")
    if set(keys) != expected_format_bound:
        raise AssertionError(
            f"manifest format/bound mismatch missing={expected_format_bound - set(keys)} "
            f"extra={set(keys) - expected_format_bound}"
        )

    accepted_funcs_seen: set[str] = set()
    mapped_nodes: set[str] = set()
    for row in manifest_rows:
        if not row.rejected_nodeids:
            raise AssertionError(f"empty rejected_nodeids for {row}")
        for nid in row.rejected_nodeids:
            if nid not in collected_set:
                # allow exact match only — no prefix fallback
                raise AssertionError(
                    f"rejected nodeid not in collected set (exact match required): {nid!r}"
                )
            if nid in mapped_nodes:
                raise AssertionError(f"nodeid mapped twice: {nid!r}")
            mapped_nodes.add(nid)
            meta = node_meta[nid]
            if meta.reachability != row.reachability or meta.bound != row.bound:
                raise AssertionError(
                    f"node {nid!r} meta {(meta.reachability, meta.bound)} "
                    f"!= manifest {(row.reachability, row.bound)}"
                )
            if meta.error_code != row.error_code:
                raise AssertionError(
                    f"node {nid!r} error_code {meta.error_code!r} "
                    f"!= manifest {row.error_code!r}"
                )
        # accepted function must appear as a function name in collected set
        if not any(_function_name_from_nodeid(n) == row.accepted_function for n in collected):
            raise AssertionError(
                f"accepted_function {row.accepted_function!r} not present in collected nodes"
            )
        accepted_funcs_seen.add(row.accepted_function)
        if row.accepted_mode not in {"same_node", "none"}:
            raise AssertionError(f"bad accepted_mode {row.accepted_mode!r}")

    # Every collected marked node must be mapped
    unmapped = collected_set - mapped_nodes
    if unmapped:
        raise AssertionError(f"collected marked nodes omitted from manifest: {sorted(unmapped)}")

    # Runtime event binding (optional — when provided)
    if runtime_events is not None:
        by_node: dict[str, list[StrongHelperEvent]] = {}
        for ev in runtime_events:
            by_node.setdefault(ev.nodeid, []).append(ev)
        for nid, meta in node_meta.items():
            evs = by_node.get(nid, [])
            if len(evs) != 1:
                raise AssertionError(
                    f"runtime: node {nid!r} expected 1 event, got {len(evs)}"
                )
            ev = evs[0]
            if ev.error_code != meta.error_code or ev.bound != meta.bound:
                raise AssertionError(
                    f"runtime event mismatch for {nid}: {ev} vs {meta}"
                )
            if ev.reachability != meta.reachability or ev.status != meta.status:
                raise AssertionError(
                    f"runtime event mismatch for {nid}: {ev} vs {meta}"
                )
        if accepted_companion_nodeids is not None:
            for row in manifest_rows:
                if row.accepted_mode != "same_node":
                    continue
                for nid in row.rejected_nodeids:
                    if nid not in set(accepted_companion_nodeids):
                        # only required when that node actually ran
                        if nid in by_node:
                            raise AssertionError(
                                f"same_node accepted companion missing for {nid!r}"
                            )


def validate_manifest_adversarial_cases(collected_nodeids: Sequence[str]) -> list[str]:
    """Run adversarial mutations on isolated copies; return list of case labels that failed as expected."""
    base_rows = default_manifest_rows_from_collected(collected_nodeids)
    proved: list[str] = []

    def expect_fail(label: str, rows: list[ManifestRow], **kwargs):
        try:
            validate_matrix(
                collected_nodeids=collected_nodeids,
                manifest_rows=rows,
                **kwargs,
            )
        except AssertionError:
            proved.append(label)
            return
        raise AssertionError(f"adversarial case {label!r} unexpectedly passed")

    # wrong error_code
    bad = list(base_rows)
    r0 = bad[0]
    bad[0] = ManifestRow(
        r0.reachability, r0.bound, "deliberately_wrong_error_code",
        r0.rejected_nodeids, r0.accepted_function, r0.accepted_mode,
    )
    expect_fail("wrong_error_code", bad)

    # nonexistent accepted function
    bad = list(base_rows)
    r0 = bad[0]
    bad[0] = ManifestRow(
        r0.reachability, r0.bound, r0.error_code,
        r0.rejected_nodeids, "does_not_exist_anywhere", r0.accepted_mode,
    )
    expect_fail("nonexistent_accepted_function", bad)

    # wrong reachability
    bad = list(base_rows)
    r0 = bad[0]
    bad[0] = ManifestRow(
        "wrong_reach", r0.bound, r0.error_code,
        r0.rejected_nodeids, r0.accepted_function, r0.accepted_mode,
    )
    expect_fail("wrong_reachability", bad)

    # wrong exact node id
    bad = list(base_rows)
    r0 = bad[0]
    bad[0] = ManifestRow(
        r0.reachability, r0.bound, r0.error_code,
        ("tests/nope.py::test_does_not_exist",), r0.accepted_function, r0.accepted_mode,
    )
    expect_fail("wrong_exact_nodeid", bad)

    # duplicate format/bound
    bad = list(base_rows) + [base_rows[0]]
    expect_fail("duplicate_format_bound", bad)

    # omit a mapped node (drop one node from first multi-node row or shrink mapping)
    bad = []
    for r in base_rows:
        if len(r.rejected_nodeids) > 1:
            bad.append(
                ManifestRow(
                    r.reachability, r.bound, r.error_code,
                    r.rejected_nodeids[1:], r.accepted_function, r.accepted_mode,
                )
            )
        else:
            bad.append(r)
    # ensure we actually omitted something
    if sum(len(r.rejected_nodeids) for r in bad) == len(collected_nodeids):
        # force omit by emptying one singleton and leaving node unmapped
        r0 = base_rows[0]
        bad = [
            ManifestRow(
                r0.reachability, r0.bound, r0.error_code,
                tuple(), r0.accepted_function, r0.accepted_mode,
            )
        ] + list(base_rows[1:])
    expect_fail("omitted_marked_node", bad)

    return proved
