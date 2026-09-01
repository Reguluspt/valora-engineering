from pathlib import Path

from app.contracts.uiux_v23 import (
    CANONICAL_CASE_STAGES,
    CANONICAL_CROSS_PRODUCT_UI_STATES,
    FORBIDDEN_NEW_BACKEND_SURFACE_MARKERS,
    LEGACY_BACKEND_CONFLICT_RATCHET,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_ROOT.parent
APP_ROOT = BACKEND_ROOT / "app"


def _runtime_python_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in APP_ROOT.rglob("*.py"):
        relative = path.relative_to(BACKEND_ROOT).as_posix()
        if relative.startswith("app/contracts/"):
            continue
        sources[relative] = path.read_text(encoding="utf-8")
    return sources


def test_canonical_v23_vocabularies_are_exact_and_unique() -> None:
    assert CANONICAL_CASE_STAGES == (
        "PRELIMINARY_REQUEST",
        "PRELIMINARY_ANALYSIS",
        "PRELIMINARY_READY",
        "OFFICIAL_INTAKE",
        "ASSET_REVIEW",
        "ASSET_WORKBENCH",
        "PRICE_EVIDENCE",
        "SUPPLIER_QUOTES",
        "SUPPLIER_SELECTION",
        "APPRAISAL_RESULT",
        "DOCUMENT_WORKSPACE",
        "DOCUMENT_SYNC_REVIEW",
        "PUBLISHING_PREPARATION",
        "PUBLISHING_EXCEPTION_REVIEW",
        "PUBLISHING_CONFIRMATION",
        "PUBLISHED",
    )
    assert len(CANONICAL_CASE_STAGES) == len(set(CANONICAL_CASE_STAGES)) == 16

    assert CANONICAL_CROSS_PRODUCT_UI_STATES == (
        "INITIAL_LOADING",
        "SECTION_LOADING",
        "BACKGROUND_REFRESH",
        "PROCESSING",
        "EMPTY_FIRST_USE",
        "EMPTY_NO_RESULTS",
        "EMPTY_NOT_APPLICABLE",
        "EMPTY_COMPLETED",
        "INLINE_ERROR",
        "SECTION_ERROR",
        "PAGE_ERROR",
        "FATAL_ERROR",
        "STALE_DATA",
        "VERSION_CONFLICT",
        "OFFLINE",
        "RECONNECTING",
        "PARTIAL_SUCCESS",
    )
    assert len(CANONICAL_CROSS_PRODUCT_UI_STATES) == 17
    assert len(set(CANONICAL_CROSS_PRODUCT_UI_STATES)) == 17


def test_legacy_backend_conflicts_cannot_expand() -> None:
    sources = _runtime_python_sources()

    for token, expected_locations in LEGACY_BACKEND_CONFLICT_RATCHET.items():
        observed = {
            relative: source.count(token)
            for relative, source in sources.items()
            if token in source
        }
        assert observed == expected_locations


def test_forbidden_backend_surfaces_are_not_introduced() -> None:
    sources = _runtime_python_sources()
    combined = "\n".join(sources.values())

    for marker in FORBIDDEN_NEW_BACKEND_SURFACE_MARKERS:
        assert marker.casefold() not in combined.casefold()

    # Authority forbids specific workflow/UI surfaces, not valid domain terminology or
    # concurrency-version fields by themselves.
    assert "NCCQ" not in FORBIDDEN_NEW_BACKEND_SURFACE_MARKERS
    assert "LOCK_VERSION" not in FORBIDDEN_NEW_BACKEND_SURFACE_MARKERS

    assert '"/case-state"' not in combined
    assert '"/resume-context"' not in combined


def test_repository_live_gates_point_to_v23_pr01_design_gate() -> None:
    live_gate_paths = (
        REPOSITORY_ROOT / "README.md",
        REPOSITORY_ROOT / "CODEX.md",
        REPOSITORY_ROOT / "ENGINEERING_GUARDRAILS.md",
        REPOSITORY_ROOT / "docs" / "design" / "VALORA_DESIGN_AUTHORITY_INDEX.md",
        REPOSITORY_ROOT / "docs" / "VALORA_PROJECT_HANDOFF.md",
    )

    for path in live_gate_paths:
        source = path.read_text(encoding="utf-8")
        current_gate = "\n".join(source.splitlines()[:100])
        assert "VALORA_UIUX_HANDOFF_v2.3.md" in current_gate
        assert "VALORA_UIUX_V2_3_AUTHORITY_INDEX.md" in current_gate
        assert "PR-00" in current_gate
        assert "CLOSED" in current_gate
        assert "PR-01" in current_gate
        assert "OWNER-ASSIGNED" in current_gate
        assert "ADR 0036" in current_gate
        assert "no migration" in current_gate.casefold()
        assert "Active runtime assignment: S13" not in current_gate

    all_live_gate_text = "\n".join(
        path.read_text(encoding="utf-8") for path in live_gate_paths
    )
    assert "active S13-PR-004 assignment" not in all_live_gate_text
    assert "S13-PR-004 is separately owner-assigned" not in all_live_gate_text
