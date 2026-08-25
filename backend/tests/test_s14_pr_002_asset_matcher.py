"""S14-PR-002 unit tests for Deterministic Explainable Asset Matcher."""
import uuid
from app.modules.taxonomy_asset_identity.domain.asset_matcher import (
    MatchLayer,
    calculate_token_similarity,
    normalize_asset_text,
    rank_candidates_deterministically,
)


def test_normalize_asset_text():
    """Verify text normalization strips accents, punctuation, and converts to lowercase."""
    assert normalize_asset_text("Máy Biến Áp 110kV (ABB)") == "may bien ap 110kv abb"
    assert normalize_asset_text("  XE TẢI   HYUNDAI 5 TẤN  ") == "xe tai hyundai 5 tan"
    assert normalize_asset_text(None) == ""


def test_calculate_token_similarity():
    """Verify token similarity calculation."""
    sim = calculate_token_similarity("Máy biến áp ABB 110kV", "Máy biến áp ABB 220kV")
    assert sim > 0.5
    assert sim < 1.0


def test_layered_candidate_precedence():
    """Verify ADR 0031 layered precedence rules."""
    pool = [
        {
            "target_id": str(uuid.uuid4()),
            "asset_name": "Máy biến áp 110kV",
            "curated_alias": "Máy biến áp 110kV",
        },
        {
            "target_id": str(uuid.uuid4()),
            "asset_name": "Thiết bị điện 110kV",
            "customer_alias": "MBA 110kV ABB",
        },
        {
            "target_id": str(uuid.uuid4()),
            "asset_name": "Máy biến áp công suất 110kV",
            "org_alias": "MBA 110kV ABB",
        },
    ]

    # Customer alias match should take highest precedence (Layer 1)
    results = rank_candidates_deterministically("MBA 110kV ABB", None, pool, top_k=3)
    assert len(results) == 3
    assert results[0].match_layer == MatchLayer.EXACT_CUSTOMER_ALIAS
    assert results[0].total_score == 1.0
    assert results[1].match_layer == MatchLayer.ORGANIZATION_ALIAS
    assert results[1].total_score == 0.95


def test_price_is_excluded_from_matching():
    """Verify that price differences do not affect candidate matching ranking."""
    pool = [
        {
            "target_id": str(uuid.uuid4()),
            "asset_name": "Máy bơm chìm Tsurumi 5kW",
            "price": 1000000.0,
        },
        {
            "target_id": str(uuid.uuid4()),
            "asset_name": "Máy bơm chìm Tsurumi 10kW",
            "price": 50000000.0,
        },
    ]

    results = rank_candidates_deterministically("Máy bơm chìm Tsurumi 5kW", None, pool, top_k=2)
    assert results[0].asset_name == "Máy bơm chìm Tsurumi 5kW"
