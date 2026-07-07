# S2-PR-001: Taxonomy + Asset Identity Design Intake Audit

## Files Read
- `manifest.json` (inside design package)
- `01_SCOPE_AND_COMPLETION_GATE.md` (beta zip)
- `09_DATA_MODEL/03_TAXONOMY_MODEL.md` (beta zip)
- `09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md` (beta zip)
- `12_API/06_TAXONOMY_API.md` (beta zip)
- `12_API/07_ASSET_IDENTITY_API.md` (beta zip)
- `16_MIGRATION_AND_SEED_PLAN.md` (beta zip)

## Git Status
- Clean tree, on branch `s1-pr-013-sprint-1-final-acceptance` (or ready to branch for Sprint 2).

## Sprint 1 Baseline Readiness
- Verified that Sprint 1 baseline is complete and fully functional.
- All 41 tests pass.
- Alembic database schema baseline matches current production-ready standard.

## Proposed Architecture for Sprint 2
- **Taxonomy Tables**:
  - `taxonomy_nodes` (PK, parent_id, level, code, names, status, is_system_seed, audit fields)
  - `asset_families` (PK, taxonomy_node_id, code, name, unit, status, seed marker, audit fields)
  - `asset_dna` (PK, asset_family_id, version, name, status, approval fields)
  - `asset_attribute_definitions` (PK, key, label, data_type, unit_id, scope, rules/enums)
  - `canonical_asset_attribute_values` (PK, canonical_asset_id, attribute_def_id, values, confidence)
  - `asset_variant_attribute_values` (PK, asset_variant_id, attribute_def_id, values, confidence)
- **Asset Identity Tables**:
  - `canonical_assets` (PK, family_id, taxonomy_node_id, standard_name, brand, manufacturer, origin, model_code, maturity, status, merge target, approval fields)
  - `asset_aliases` (PK, canonical_asset_id, asset_variant_id, alias_scope, alias_text, alias_type, normalized_alias, source fields, status)
  - `identity_candidates` (PK, project_asset_line_id, candidate_type, canonical_asset_id, asset_variant_id, taxonomy_node_id, proposed fields, confidence, reasons, conflicts, rank, status)
  - `similarity_scores`
  - `duplicate_candidates`
  - `merge_decisions` (source_asset_id, target_asset_id, reason, decision_status, alias preservation flags)
  - `identity_review_items`
  - `identity_decision_logs`
- **ProjectAssetLine Schema Extension**:
  - Add fields for suggested/approved CanonicalAsset, AssetVariant, and TaxonomyNode IDs, along with status (`review_status`, `validation_status`) and lineage tracking.
- **API Router Paths**:
  - `/api/v1/taxonomy/nodes` (CRUD, submit-review, approve, deprecate)
  - `/api/v1/taxonomy/variants` (CRUD, submit-review, approve)
  - `/api/v1/asset-identity/candidates` (generate-bulk, batch-approve, reject)
  - `/api/v1/asset-identity/assets` (add aliases, merge)

## Scope Verification
- Confirming that Knowledge, Quotes, Appraised price calculations, Document rendering, and external crawling are strictly Out of Scope for Sprint 2.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready to begin Sprint 2 implementation phase.
