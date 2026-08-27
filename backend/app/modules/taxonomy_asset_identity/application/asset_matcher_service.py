"""S14-PR-002 Application service for Deterministic Explainable Asset Matcher."""
from __future__ import annotations

import uuid
from typing import Any, Sequence
from sqlalchemy.orm import Session

from app.modules.taxonomy_asset_identity.domain.asset_matcher import (
    MatchCandidate,
    rank_candidates_deterministically,
)
from app.modules.excel_import.models import ContextualAssetAlias


def match_asset_identity(
    db: Session,
    *,
    org_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
    raw_asset_name: str,
    raw_unit: str | None = None,
    candidate_pool: Sequence[dict[str, Any]],
    top_k: int = 5,
) -> list[MatchCandidate]:
    """Retrieve and rank candidates for a raw asset observation.

    Checks database contextual aliases for org_id and customer_id before fallback ranking.
    NO database writes are performed (read-only query).
    """
    enriched_pool: list[dict[str, Any]] = []

    # Query customer-specific and org-level contextual aliases
    aliases = (
        db.query(ContextualAssetAlias)
        .filter(
            ContextualAssetAlias.organization_id == org_id,
            ContextualAssetAlias.status == "active",
        )
        .all()
    )

    alias_by_target: dict[uuid.UUID, dict[str, str]] = {}
    for alias in aliases:
        target_id = alias.canonical_asset_id or alias.asset_variant_id
        if target_id:
            if alias.customer_id and alias.customer_id == customer_id:
                alias_by_target.setdefault(target_id, {})["customer_alias"] = alias.alias_name
            elif alias.customer_id is None:
                alias_by_target.setdefault(target_id, {})["org_alias"] = alias.alias_name

    for item in candidate_pool:
        item_copy = dict(item)
        target_id_str = item.get("target_id")
        if target_id_str:
            try:
                target_uuid = uuid.UUID(target_id_str)
                if target_uuid in alias_by_target:
                    item_copy.update(alias_by_target[target_uuid])
            except (ValueError, TypeError):
                pass
        enriched_pool.append(item_copy)

    return rank_candidates_deterministically(
        raw_wording=raw_asset_name,
        raw_unit=raw_unit,
        candidate_pool=enriched_pool,
        top_k=top_k,
    )
