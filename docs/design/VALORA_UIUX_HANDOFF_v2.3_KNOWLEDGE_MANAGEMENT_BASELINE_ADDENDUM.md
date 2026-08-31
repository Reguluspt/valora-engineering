# VALORA UI/UX Handoff v2.3 — Knowledge Management Baseline Addendum

**Baseline:** `Quản lý Kho tri thức — Iteration 1`  
**Status:** Design Authority / P0 UI/UX baseline  
**Date:** 31/08/2026  
**Scope:** Knowledge-management workspace aligned with `taxonomy_asset_identity`, `knowledge_evidence`, `document_engine_intelligence` and existing v1.4 Knowledge Memory authority.

## 1. Purpose

`Quản lý Kho tri thức` is the dedicated knowledge-management workspace. It is distinct from the `Kho tri thức` panel embedded in the asset Workbench.

- Workbench `Kho tri thức` panel = consumer/search surface for the currently selected asset.
- `Quản lý Kho tri thức` = management/review surface for canonical assets, variants, aliases, review candidates, historical-dossier knowledge and lineage/version history.

The screen must remain single-user and Vietnamese-first. AI/rules may suggest, explain, rank or extract; they may not activate official knowledge or silently overwrite human-confirmed data.

## 2. Information architecture

Top-level views:

1. `Tài sản chuẩn`
2. `Cần rà soát`
3. `Hồ sơ cũ`
4. `Lịch sử & nguồn gốc`

These are views inside one Knowledge Management workspace, not mandatory lifecycle checkpoints in the appraisal case flow.

### 2.1 Tài sản chuẩn

Primary management surface for confirmed canonical knowledge:

- Canonical Asset;
- Asset Variant;
- approved/contextual aliases;
- structured KTKT attributes;
- source/lineage and knowledge version metadata.

The list is table/list-first and supports search/filter. Selecting an asset opens the asset detail workspace without navigating to a separate product shell.

### 2.2 Cần rà soát

Review queue for candidates that require a user decision, including identity candidates, contextual-alias candidates and knowledge candidates extracted from historical dossiers.

No high-confidence candidate may become active knowledge without an explicit user decision.

### 2.3 Hồ sơ cũ

Management/review surface for historical paired dossiers and extracted knowledge candidates. Historical sources remain source-backed and versioned; they are not injected directly into active knowledge.

### 2.4 Lịch sử & nguồn gốc

Provides lineage, version and activity visibility: source dossier/file/locator, confirmed actor/time, current/superseded version and usage references.

## 3. Baseline layout — `Tài sản chuẩn`

Desktop Fluent 2 layout:

- VALORA left navigation.
- Header/breadcrumb: `Kho tri thức > Quản lý kho tri thức`.
- Top tabs: `Tài sản chuẩn / Cần rà soát / Hồ sơ cũ / Lịch sử & nguồn gốc`.
- Left column: canonical-asset list with search/filter and compact status.
- Center: selected asset detail.
- Right: `Xem trước theo Báo cáo thẩm định giá` + management metadata.

Asset-detail tabs:

- `Thông tin chung`
- `Đặc điểm KTKT`
- `Biến thể`
- `Alias`
- `Nguồn gốc & phiên bản`

## 4. Structured KTKT authority

The Knowledge Base must not store `Đặc điểm kinh tế - kỹ thuật` only as one opaque narrative string.

It must support structured business attributes, including:

### 4.1 General identity attributes

Examples:

- Thương hiệu
- Xuất xứ
- Mã sản phẩm/model
- Loại thiết bị

### 4.2 Technical attributes

Technical attributes are extensible by asset type and may be grouped, for example:

- Hiển thị
- Hệ điều hành & tính năng
- Kết nối
- Kích thước & khối lượng
- Bảo hành
- other domain-appropriate groups

Each attribute conceptually supports at least:

`group | attribute name | value | unit | ordering | source/lineage`

The UI must not hard-code a TV-only schema. Different asset types can have different attribute sets.

## 5. Report-preview authority

The asset-detail workspace includes `Xem trước theo Báo cáo thẩm định giá`.

This is a view-only preview of how the selected structured asset data will be rendered into the company report template. It is not a fake Word editor.

The preview follows the company report structure demonstrated and approved by the owner:

`Tên tài sản | Đặc điểm kinh tế - kỹ thuật | Đvt | SL`

Within `Đặc điểm kinh tế - kỹ thuật`, the presentation mapping follows the report convention:

```text
– Thuộc tính cấp 1: Giá trị.
– Thuộc tính cấp 1: Giá trị.
– Thông số kỹ thuật:
    + Thuộc tính: Giá trị.
    + Thuộc tính: Giá trị.
```

The exact visible wording, indentation, bullets, borders, table dimensions and pagination remain governed by the approved Microsoft 365 company template.

## 6. Data vs presentation separation

Binding rule:

```text
Structured knowledge/business data
→ user review/confirmation
→ document presentation mapping
→ managed region / report template
→ Word file managed by Microsoft 365
```

Knowledge storage owns structured data and lineage. The report template owns presentation.

Do not store the entire preformatted Word paragraph as the primary knowledge truth merely to preserve visual formatting.

## 7. Fill / document-generation requirements

When structured KTKT data is filled into the appraisal report, the generation/fill pipeline must preserve the company template's presentation contract, including where applicable:

- report table and column structure;
- exact column labels;
- font and size inherited from the template;
- paragraph alignment and indentation;
- `–` and `+` hierarchy/bullets;
- line spacing;
- cell widths;
- borders;
- row/page continuation behavior;
- page layout and pagination rules.

Long KTKT content may continue to subsequent pages according to the template, but the engine must not convert the company table into cards or unrelated free-form paragraphs.

This extends the existing Fill Engine rule that VALORA must preserve formulas/features/styles/layout and must warn before execution when the required template behavior cannot be preserved.

## 8. Human/AI boundaries

- AI may extract, normalize, suggest attribute grouping, propose aliases and explain matches.
- AI may not silently activate canonical knowledge.
- AI may not overwrite the customer's immutable raw wording/source observation.
- AI may not change company report formatting authority.
- A committed human decision is required for identity/knowledge activation.

## 9. Relationship to existing code-base authority

This baseline is intended to surface, not replace, the domain boundaries already defined by:

- Column Mapping Memory;
- Raw Asset Observation;
- Asset Identity Memory;
- CanonicalAsset / AssetVariant / AssetAlias / ContextualAssetAlias;
- IdentityCandidate / SimilarityScore / IdentityReviewItem / IdentityDecisionLog;
- DossierBundle / DossierRowAlignment;
- reviewed quote/spec/knowledge candidates and activation.

Direct active-knowledge injection remains forbidden.

## 10. Navigation semantics

`Quản lý Kho tri thức` is a horizontal/supporting module. It is not inserted as a mandatory checkpoint in the case north-star flow.

Workbench uses the Knowledge Base for contextual retrieval. Knowledge Management receives review candidates and historical knowledge independently.

## 11. Guardrails

- Single-user workflow.
- Vietnamese-first.
- Fluent 2, desktop-first, data-heavy/table-first.
- One primary CTA per context.
- No silent accept/activation/overwrite.
- No fake Word editor.
- Historical price/knowledge is support evidence and does not override v2.3 price-source authority.
- Structured KTKT is business data; report formatting belongs to the company template.

## 12. ADR trigger

Evaluate an ADR before implementation if this design requires changes to:

- canonical/variant/attribute persistence schema;
- knowledge-version activation semantics;
- attribute ordering/grouping persistence;
- source-lineage model;
- document presentation-mapping contract;
- managed-region storage or merge semantics;
- versioning/transaction boundaries between knowledge activation and document generation.
