# VALORA v2.3 visual reference bundle

This directory preserves the Product Owner-provided PDF copies and reproducible page renders used by VF0 visual acceptance. The PDFs are unmodified implementation and visual references. The PNGs are renders of approved mockup pages, not new designs. Compare the embedded product screen and its regions; the PDF page heading and margins are not application chrome.

## Authority and precedence

These files are **non-canonical**. They do not replace or outrank live `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, the canonical [`VALORA_UIUX_HANDOFF_v2.3.md`](../../VALORA_UIUX_HANDOFF_v2.3.md), [`VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`](../../VALORA_UIUX_V2_3_AUTHORITY_INDEX.md), current governing addenda, or accepted ADR/domain contracts. The current explicit Product Owner decision governs its named scope. If wording or sample data in a visual reference conflicts with current semantic or domain authority, that authority wins. Visual composition still matters where an approved baseline applies.

The canonical master reconciled Part 2C's `PR-00 → PR-13` execution sequence as historical; the Unified Roadmap controls current sequencing. Part 1 appendix B contains historical iterations and a removed S14 mockup. Part 2B's **Orchestration Hub Iteration 2** supersedes Part 1's S10 composition. Part 1's **NCCQ Iteration 6** supersedes its earlier NCCQ iterations.

## Source PDFs

SHA-256 was calculated from each original file and verified against the byte-for-byte repository copy.

| Source filename | SHA-256 | Authority role | Relevant pages and current iteration |
| --- | --- | --- | --- |
| [VALORA_UIUX_Handoff_v2.3_RELEASE_CONFIRMATION_BASELINE_Part_1.pdf](VALORA_UIUX_Handoff_v2.3_RELEASE_CONFIRMATION_BASELINE_Part_1.pdf) | `D4A02DC3D7003FEEB83BA2D61B9C4AEBCED6133CD97799E5E405C08E16E03CDF` | Approved visual appendix, subject to newer canonical/addendum authority | PDF pp. 13–17: S11, S12, S13, Price & Evidence, NCCQ Iteration 6. PDF p. 12 S10 is superseded by Part 2B p. 3. |
| [VALORA_UIUX_Handoff_v2.3_AUDIT_LINEAGE_ENTRYPOINT_BASELINE_Part_2B.pdf](VALORA_UIUX_Handoff_v2.3_AUDIT_LINEAGE_ENTRYPOINT_BASELINE_Part_2B.pdf) | `026C0E4A9559654030E11A712536A8761ACED09D8815180DFC83981B115CB530` | Newer approved screen and cross-product visual boards, subject to canonical semantics | PDF p. 2 NCC Selection Iteration 1; p. 3 S10 Orchestration Hub Iteration 2; p. 6 State Pattern Board Iteration 1; p. 8 M365 Return/Revalidation Iteration 1; p. 10 Audit/Lineage Entry-point Pattern Board Iteration 1. |
| [VALORA_UIUX_Handoff_v2.3_FINAL_NORTH_STAR_IMPLEMENTATION_CLOSURE_Part_2C.pdf](VALORA_UIUX_Handoff_v2.3_FINAL_NORTH_STAR_IMPLEMENTATION_CLOSURE_Part_2C.pdf) | `55D3BFB51E131B698CCE120629A741AF7ED57280A40851EA4004E2BFE31116BF` | Historical design-to-engineering gap and implementation closure reference; no active whole-screen pixel baseline | PDF pp. 1–8, Final North-star Audit and implementation gap closure, dated 01/09/2026. Its PR ordering is superseded by the current roadmap. |

Page numbers are **PDF page numbers**, counted from 1.

## Current visual baselines

Each PNG is a full approved PDF page rendered at 144 DPI (2× PDF points), RGB, without alpha, using PyMuPDF 1.27.2.2. Filenames are stable. The render contains the PDF's mockup and surrounding explanatory material.

| Production surface or pattern | Authority type | Current iteration and source page | Repository-local image |
| --- | --- | --- | --- |
| S10 Case Overview | `EXACT_VISUAL_BASELINE` | Orchestration Hub Iteration 2, Part 2B p. 3 | [s10-orchestration-hub-iteration-2-approved.png](baselines/s10-orchestration-hub-iteration-2-approved.png) |
| S11 Asset Confirmation | `EXACT_VISUAL_BASELINE` | Approved appendix A.2, Part 1 p. 13 | [s11-asset-confirmation-approved.png](baselines/s11-asset-confirmation-approved.png) |
| S12 Workbench | `EXACT_VISUAL_BASELINE` | Approved appendix A.3, Part 1 p. 14 | [s12-workbench-approved.png](baselines/s12-workbench-approved.png) |
| S13 Asset Context Drawer within S12 | `EXACT_VISUAL_BASELINE` | Approved appendix A.4, Part 1 p. 15 | [s13-asset-context-drawer-approved.png](baselines/s13-asset-context-drawer-approved.png) |
| Price & Evidence | `EXACT_VISUAL_BASELINE` | Approved appendix A.5, Part 1 p. 16 | [price-evidence-approved.png](baselines/price-evidence-approved.png) |
| NCCQ Supplier Quote Management | `EXACT_VISUAL_BASELINE` | Iteration 6, Part 1 p. 17 | [nccq-iteration-6-approved.png](baselines/nccq-iteration-6-approved.png) |
| NCC Selection | `EXACT_VISUAL_BASELINE` | Iteration 1, Part 2B p. 2 | [ncc-selection-iteration-1-approved.png](baselines/ncc-selection-iteration-1-approved.png) |
| Cross-product states | `VISUAL_GRAMMAR_ONLY` for each host screen | State Pattern Board Iteration 1, Part 2B p. 6 | [cross-product-state-pattern-board-iteration-1.png](baselines/cross-product-state-pattern-board-iteration-1.png) |
| M365 Word Return/Revalidation state | `EXACT_VISUAL_BASELINE` for the approved Word return state board; `VISUAL_GRAMMAR_ONLY` for the surrounding Workspace and the separate OAuth connection callback | Iteration 1, Part 2B p. 8 | [m365-return-revalidation-iteration-1.png](baselines/m365-return-revalidation-iteration-1.png) |
| Audit/Lineage entry points | `VISUAL_GRAMMAR_ONLY` within their host screens | Pattern Board Iteration 1, Part 2B p. 10 | [audit-lineage-entrypoint-pattern-board-iteration-1.png](baselines/audit-lineage-entrypoint-pattern-board-iteration-1.png) |

The **Price & Evidence** PNG is an exact baseline for its approved standalone screen. The current VF0 runtime exposes only a smaller Workbench price/evidence context tab; that tab uses the approved visual grammar and does not claim whole-screen parity. Its absent Internet/old-dossier/evidence capabilities are outside VF0. The NCC Selection primary commit action appears only after a human selects an eligible quote; an unopened or unselected drawer is not evidence that the action is missing.

## Production surfaces without an exact approved mockup in this bundle

The AppShell and project-list/workbench entry use the approved global VALORA Fluent 2 light visual grammar and the applicable screen baselines above. S02, S03, S04, and S05 are each `VISUAL_GRAMMAR_ONLY`: the canonical handoff inventories them as product surfaces but these source documents do not supply an approved exact whole-screen mockup for them. S09 is `VISUAL_GRAMMAR_ONLY_WITH_APPROVED_LAYOUT_CONTRACT`: Part 1 PDF p. 4 and the canonical v2.3 master establish the approved S09 information groups and semantics, but the three persisted PDFs contain no exact S09 whole-screen mockup. Apply the shared shell, compact desktop table/form density, status, spacing, contextual panels, and action hierarchy without inventing business sections. Do not label these candidate screenshots as pixel matches.

| Surface | Authority type | Current iteration/reference |
| --- | --- | --- |
| AppShell and Project List entry | `VISUAL_GRAMMAR_ONLY` | Current Fluent 2 light product grammar; S10/S12/S11 shell examples |
| S02 Quản lý yêu cầu sơ bộ | `VISUAL_GRAMMAR_ONLY` | Current v2.3 canonical flow and shared product grammar |
| S03 Tạo yêu cầu sơ bộ | `VISUAL_GRAMMAR_ONLY` | Current v2.3 canonical flow and shared product grammar |
| S04 Upload & Mapping Excel | `VISUAL_GRAMMAR_ONLY` | Current G1.1H mapping contract and shared product grammar |
| S05 Phân tích danh mục | `VISUAL_GRAMMAR_ONLY` | Current G1.1I analysis contract and shared product grammar |
| S09 Kết quả sơ bộ → Chuyển sang thẩm định chính thức | `VISUAL_GRAMMAR_ONLY_WITH_APPROVED_LAYOUT_CONTRACT` | Part 1 PDF p. 4, S09 approved information layout and canonical v2.3 semantics; no exact S09 mockup image in this bundle |
| Workbench price/evidence context tab | `VISUAL_GRAMMAR_ONLY` | Current Workbench panel; Part 1 p. 16 is an exact reference for a separate full screen |
| M365 Workspace and OAuth connection callback | `VISUAL_GRAMMAR_ONLY` | Current M365 runtime; Part 2B p. 8 specifically depicts Word return/revalidation |

Candidate screenshot evidence must cite the applicable **repository-local** PDF and PNG paths from this bundle, including the PDF page and iteration. A remembered image from a chat session is not acceptance evidence.
