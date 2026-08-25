"""S14-PR-002 Pure domain logic for Deterministic Explainable Asset Matcher."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence


class MatchLayer(str, Enum):
    EXACT_CUSTOMER_ALIAS = "exact_customer_alias"
    ORGANIZATION_ALIAS = "organization_alias"
    CURATED_ALIAS = "curated_alias"
    CANONICAL_NAME_OR_CODE = "canonical_name_or_code"
    FUZZY_ATTRIBUTE_SCORE = "fuzzy_attribute_score"


@dataclass(frozen=True)
class MatchCandidate:
    candidate_id: str
    target_type: str  # "CanonicalAsset" or "AssetVariant"
    target_id: str
    asset_name: str
    asset_code: str | None
    match_layer: MatchLayer
    total_score: float  # 0.0 to 1.0
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()


def normalize_asset_text(text: str | None) -> str:
    """Normalize asset text for deterministic matching (lowercase, strip diacritics/punctuation)."""
    if not text:
        return ""
    # Normalize unicode to NFD and drop diacritics
    nfkd = unicodedata.normalize("NFD", text.lower().strip())
    without_diacritics = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    # Replace non-alphanumeric with spaces
    cleaned = re.sub(r"[^\w\s]", " ", without_diacritics)
    return " ".join(cleaned.split())


def calculate_token_similarity(query: str, target: str) -> float:
    """Calculate token overlap similarity ratio between query and target strings."""
    norm_q = set(normalize_asset_text(query).split())
    norm_t = set(normalize_asset_text(target).split())
    if not norm_q or not norm_t:
        return 0.0
    intersection = norm_q & norm_t
    union = norm_q | norm_t
    return len(intersection) / len(union)


def rank_candidates_deterministically(
    raw_wording: str,
    raw_unit: str | None,
    candidate_pool: Sequence[dict[str, Any]],
    top_k: int = 5,
) -> list[MatchCandidate]:
    """Rank candidate items deterministically based on layered precedence and explainable scores.
    
    Layer Priority (ADR 0031 §4):
    1. same-customer contextual alias
    2. organization contextual alias
    3. curated AssetAlias
    4. canonical/variant names and codes
    5. deterministic fuzzy/attribute retrieval
    
    Price is EXCLUDED as an identity feature.
    """
    normalized_query = normalize_asset_text(raw_wording)
    if not normalized_query or not candidate_pool:
        return []

    results: list[MatchCandidate] = []

    for item in candidate_pool:
        target_type = item.get("target_type", "CanonicalAsset")
        target_id = str(item.get("target_id", ""))
        name = item.get("asset_name", "")
        code = item.get("asset_code")
        customer_alias = item.get("customer_alias")
        org_alias = item.get("org_alias")
        curated_alias = item.get("curated_alias")

        norm_name = normalize_asset_text(name)
        norm_cust_alias = normalize_asset_text(customer_alias) if customer_alias else ""
        norm_org_alias = normalize_asset_text(org_alias) if org_alias else ""
        norm_curated_alias = normalize_asset_text(curated_alias) if curated_alias else ""

        match_layer: MatchLayer
        total_score: float
        breakdown: dict[str, Any] = {}
        reasons: list[str] = []

        if norm_cust_alias and normalized_query == norm_cust_alias:
            match_layer = MatchLayer.EXACT_CUSTOMER_ALIAS
            total_score = 1.0
            breakdown = {"exact_customer_alias": 1.0, "similarity": 1.0}
            reasons.append("Chớp trùng khớp hoàn toàn với tên alias của khách hàng.")
        elif norm_org_alias and normalized_query == norm_org_alias:
            match_layer = MatchLayer.ORGANIZATION_ALIAS
            total_score = 0.95
            breakdown = {"organization_alias": 0.95, "similarity": 0.95}
            reasons.append("Trùng khớp với mẫu tên thay thế của tổ chức.")
        elif norm_curated_alias and normalized_query == norm_curated_alias:
            match_layer = MatchLayer.CURATED_ALIAS
            total_score = 0.90
            breakdown = {"curated_alias": 0.90, "similarity": 0.90}
            reasons.append("Trùng khớp với danh mục Alias chuẩn hóa.")
        elif (code and normalized_query == normalize_asset_text(code)) or (norm_name and normalized_query == norm_name):
            match_layer = MatchLayer.CANONICAL_NAME_OR_CODE
            total_score = 0.85
            breakdown = {"name_or_code_match": 0.85, "similarity": 0.85}
            reasons.append("Trùng khớp tên tài sản hoặc mã tài sản chuẩn.")
        else:
            match_layer = MatchLayer.FUZZY_ATTRIBUTE_SCORE
            sim = calculate_token_similarity(raw_wording, name)
            total_score = round(sim * 0.80, 4)
            breakdown = {"token_similarity": sim, "weighted_score": total_score}
            reasons.append(f"Khớp độ tương đồng từ vựng: {int(sim * 100)}%.")

        results.append(
            MatchCandidate(
                candidate_id=f"cand-{target_id}",
                target_type=target_type,
                target_id=target_id,
                asset_name=name,
                asset_code=code,
                match_layer=match_layer,
                total_score=total_score,
                score_breakdown=breakdown,
                reasons=tuple(reasons),
            )
        )

    # Sort deterministically by layer weight (descending) then total_score (descending)
    layer_order = {
        MatchLayer.EXACT_CUSTOMER_ALIAS: 5,
        MatchLayer.ORGANIZATION_ALIAS: 4,
        MatchLayer.CURATED_ALIAS: 3,
        MatchLayer.CANONICAL_NAME_OR_CODE: 2,
        MatchLayer.FUZZY_ATTRIBUTE_SCORE: 1,
    }

    results.sort(
        key=lambda c: (layer_order[c.match_layer], c.total_score, c.asset_name),
        reverse=True,
    )
    return results[:top_k]
