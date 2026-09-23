# VALORA Appraisal OS — Unified Reconciliation & Development Roadmap v2.3

**Status:** CURRENT ROADMAP / PRODUCT-ENGINEERING DIRECTION
**Last reconciled:** 2026-09-23
**Roadmap authority:** this Unified Roadmap v2.3 supersedes v2.2 for development ordering while preserving its reconciled decisions
**Integrated sub-domain:** Report Template Recognition / Fill Engine technical direction
**Repository state (reconciled 2026-09-23):** `origin/main` remains merged through PR #31 at `27d1cc6…`; active Draft PR #32 remains against `main`, while integration branch `feat/operational-frontend-m365` is at `d725bbc6…` after F2-PR-001 (#34), F2-PR-002 (#36) and F2-PR-003 (#38) merged into that integration branch. This is not claimed as merged to `main`.

## 1. Executive decision

VALORA uses one product roadmap:

> Appraisal OS ordering wins. Template Recognition / Fill Engine is a Document & Template platform
> sub-roadmap and must not replace the North-star business roadmap.

Keep the generic template architecture, Template IR, deterministic Fill Engine, multi-signal locator,
Office intelligence sidecar, Template Family, visual QA and AI mapping candidates, but place them at
the correct point in the Appraisal OS sequence.

Global direction:

```text
Authority cleanup
→ Pre-case product closure
→ Appraisal Core vertical slices
→ Document Runtime
→ Release / Publishing
→ Template Intelligence / Fidelity expansion
→ Product E2E completion
→ Valora Intelligence Platform & Assistant
```

## 2. Authority roles and non-negotiable model

Conflict resolution / role split:

```text
1. Explicit current Product Owner decision — wins only in the scope it names
2. `CODEX.md`
3. `ENGINEERING_GUARDRAILS.md`
4. Current UI/UX Handoff v2.3
5. Current UI/UX v2.3 Authority Index
6. Applicable current v2.3 addendum
   → product semantics, workflow, IA, interaction and visual baseline
7. This Unified Roadmap v2.3
   → development sequencing and architecture integration
8. `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md`
   → OS-G7 / AI-readiness architecture detail only; not runtime authorization
9. Accepted scoped ADR
10. Current task / implementation contract
11. Current handoff / acceptance evidence
12. Historical Design Book / sprint / audit / remediation / research evidence
```

`VALORA_UIUX_Handoff_v2.3` therefore answers **what the product must be**; this roadmap answers **what to build first and how the architecture is integrated**. The older Part 2C `PR-00 → PR-13` sequence is superseded for ordering only; its still-current UX/business contracts and acceptance invariants remain valid.

- VALORA owns authoritative business facts.
- PostgreSQL + append-only `DocumentRevision` + `DocumentRevisionCurrentHead` own accepted
  document-version authority.
- App-owned immutable blobs hold exact accepted revision bytes.
- Word/Excel/OneDrive are external ports/surfaces, never business authority.
- AI and Office analysis tools produce observations/proposals, not authoritative decisions.
- Human/domain commands control official mutation.
- Case State is computed from authoritative facts; do not add a synthetic workflow-state database.
- Do not revive Review Queue, standalone Validation Dashboard, KSCL workflow, reviewer workflow,
  multi-level approval, NCCQ intermediate workflow, global Audit screen, standalone progress/version-lock screens.
- New infrastructure/provider abstractions are allowed only when a concrete North-star slice cannot
  close safely without them.
- Product visual authority is **Microsoft Fluent 2 light**, desktop-first, Vietnamese-first, data-heavy/table-first. Approved v2.3 mockups/baselines govern shell, navigation, density, tables, drawers, command bars and states. Astryx is not product visual authority; any retained Astryx primitive must be visually remapped to Fluent 2 light.

## 3. Current engineering state

### Merged main

`origin/main` accepted merged baseline remains PR #31 at
`27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6`.

### Active Draft PR #32 / integration branch

PR #32 remains open/draft against `main`. Integration branch exact head is `d725bbc6f60f2a21ec11a555d9565d2ab01470ae`; exact-head CI #454 is SUCCESS. F2-PR-001/#34, F2-PR-002/#36 and F2-PR-003/#38 are merged into that integration branch only.

Contains:
- Operational Frontend candidate;
- Local immutable DocumentBlobStore;
- OneDrive Personal Exchange;
- current Design Authority/ADR reconciliation.

Milestones:
- Local storage G6: **ACCEPTED** on exact reviewed snapshot `d71a42e...`;
- OneDrive Exchange G8: **OFFLINE COMPLETE** at code milestone `f896f15...`;
- ADR 0045: **ACCEPTED DESIGN / RUNTIME CONTRACT REQUIRED**.

G8 proves storage/Exchange machinery. It does not authorize automatic authoritative promotion of a
changed Working DOCX.

## 4. Canonical document lifecycle

### 4.1 Template authoring

```text
Immutable Template Source
→ Structural Analysis
→ Template IR
→ TemplateMappingCandidate
→ Human Mapping Review
→ CompiledTemplateManifest
→ Test Fill
→ Structural / Visual Validation
→ explicit activation
→ ACTIVE Template Version
```

AI may create mapping candidates. AI does not activate templates.

### 4.2 Production generation

```text
ACTIVE Template Version
+ CompiledTemplateManifest
+ authoritative DataSnapshot
+ FillEngineVersion
→ RenderJob
→ GeneratedDocumentCandidate
→ structural/visual verification
→ explicit Generate / Accept Version command
→ immutable DocumentRevision N+1
→ CurrentHead
```

Hard rule:

```text
RenderJob complete != accepted DocumentRevision
```

### 4.3 Working Word

ADR 0045 governs external Word edits:

```text
Authoritative Revision N
→ Working copy
→ user edits + Save
→ provider signal / focus / freshness trigger
→ Auto Revalidation
→ verified DOCX analysis
→ Managed Region diff
→ Old / V / W
→ DocumentChangeCandidate
→ rule/AI recommendation
→ Human Review / Conflict Decision
→ explicit accepted domain/revision command
→ immutable Revision N+1
```

Word Save, provider notification, revalidation and candidate creation are non-authoritative.

### 4.4 Release

```text
Accepted DocumentRevision(s)
→ ReleasePlan
→ Readiness
→ ReleaseExceptionDecision if needed
→ exact-revision ReleaseManifest
→ explicit Publish
→ immutable PUBLISHED projection
```

`DocumentRevision != Export != ReleaseManifest != Published`.

## 5. Candidate vocabulary

Do not collapse the following into one generic aggregate.

### TemplateMappingCandidate
Template-authoring question: which canonical field/ownership/region contract maps to this template area?

### GeneratedDocumentCandidate
Generation question: is this deterministic output safe and ready to become an accepted document revision?

### DocumentChangeCandidate
Working-runtime question: what changed in Word relative to authoritative VALORA facts and the accepted baseline?

## 6. Word ownership model

### MANAGED
VALORA owns authoritative business value. Word edits are proposals/observations and cannot silently
become domain truth.

### INITIAL_ONLY
VALORA fills initial content; later Word edits are preserved unless another explicit contract says otherwise.

### USER_OWNED
User narrative is Word-owned. VALORA does not silently overwrite it.

`REPEATING_COLLECTION`, `COMPUTED` and `CONDITIONAL` are semantic/render types, not separate
ownership authorities.

## 7. Template IR

Canonical relationship:

```text
Immutable Template Source + SHA-256
→ Template IR
  (VALORA-controlled normalized structural interpretation)
→ confirmed mapping
→ CompiledTemplateManifest
```

TIR does not replace immutable source evidence. Source/version change makes derived analysis/mapping
stale until re-analysis/transfer/confirmation.

## 8. Office intelligence boundary

OfficeCLI or another analyzer may be used behind an `OfficeStructureProvider` port.

Initial allowed scope:
- validate;
- read structure/view/query;
- read-only dump;
- HTML/PNG render.

Initial denied scope:
- production mutation;
- authoritative template mutation;
- automatic fill authority.

Pin version/binary hash and deny uncontrolled auto-update. Production dependence requires a bounded
read-only conformance gate first.

## 9. Excel boundary

Do not replace the existing safe Excel business-intake pipeline.

```text
XLSX
├─ Safe Business Intake → existing openpyxl staging / explicit Apply
└─ optional Office Intelligence → structural/layout analysis only
```

Office intelligence is not spreadsheet calculation authority.

## 10. Stage completion contract

A canonical stage is green only when all five axes are green:

1. durable Domain Fact;
2. Application/API;
3. Product Surface — conforms to current UI/UX Design Authority and Fluent 2 light baseline;
4. OS Integration — Case State + Next Action + blocker/warning/stale + Resume;
5. Acceptance — tests/browser/E2E appropriate to the slice, including visual regression for authority-defined golden screens.

A model/table/API alone is not product completion.

## 11. Unified roadmap

### OS-G0 — Authority, visual-system & branch reconciliation

Execution contract: `docs/implementation/VALORA-FLUENT2-REMEDIATION-001.md`.
Code inventory: `docs/audits/2026-09-22__FRONTEND_ASTRYX_TO_FLUENT2_CODE_INVENTORY.md`.

- reconcile PR #32 title/body/scope;
- explicitly supersede old Astryx product-visual authority in engineering guidance; keep Astryx only as low-level primitive if fully remapped;
- freeze a Fluent 2 light implementation contract: light semantic tokens, typography, density, shell/navigation, table/grid, drawer, command bar, button, status and state patterns;
- remediate golden authority surfaces before adding broad new frontend capability: S10, S12, S13, NCCQ/NCC Selection and Không gian tài liệu/M365 Return;
- add screenshot/visual-regression acceptance so dark/cyan/glassmorphic drift cannot pass as compliant;
- keep G8 immutable storage/CAS/idempotency/recovery machinery;
- freeze `VALORA-DOCUMENT-CHANGE-OBSERVATION-001` implementation contract;
- remove active legacy Review Queue / Validation Dashboard / old S13 IA;
- use provider-neutral `Không gian tài liệu` / Document Workspace naming; Microsoft 365 is an integration, not the domain name;
- record that Part 2C `PR-00 → PR-13` sequencing is historical/superseded for ordering only;
- no automatic G9 live AppFolder;
- no broad Template/Office platform implementation yet.

### OS-G1 — Pre-case Product Closure

```text
Trang chủ
→ Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu
→ Upload & Mapping Excel
→ Phân tích danh mục
→ Rà soát tích hợp
→ Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức
→ Tổng quan hồ sơ
```

Close facts → APIs → UI → Case State → Next Action → lineage → browser acceptance.

### OS-G2 — Appraisal Core

Close vertically:

```text
ASSET_REVIEW
→ ASSET_WORKBENCH
→ PRICE_EVIDENCE
→ SUPPLIER_QUOTES
→ SUPPLIER_SELECTION
→ APPRAISAL_RESULT
```

The final Appraisal Result must expose authoritative data that can feed a document `DataSnapshot`.

### OS-G3 — Document Runtime

When the business loop reaches the document critical path:

#### DOC-G1 Office analyzer read-only proof
Use the first real report template as golden evidence. Prove source immutability, deterministic
structure extraction, tables/merge/header/footer/fields/images, bounded resources and reference-render comparison.

#### DOC-G2 Template IR + locator
Create TIR v1, normalizer, structural fingerprints and multi-signal locator.

#### DOC-G3 Golden structural baseline
Golden fixtures are evidence, never implementation authority.

#### DOC-G4 Data Model Registry
Stable canonical Field IDs, datatype/cardinality/sensitivity/allowed document roles/formatter contract.

#### DOC-G5 Compiler
Compile confirmed mappings into `CompiledTemplateManifest`. Initial mapping may be human-driven.

#### DOC-G6 Deterministic Fill Engine
Minimum DOCX features:
- scalar;
- repeating rows;
- ownership enforcement;
- deterministic formatters;
- bounded conditional/computed rules;
- immutable candidate output.

No runtime LLM.

#### DOC-G7 Verification
Minimum structural + visual acceptance before official generation.

#### DOC-G8 Generation / Revision boundary
`GeneratedDocumentCandidate → explicit accept → DocumentRevision`.

#### DOC-G9 Working Change Review
Implement ADR 0045:
notification/focus/freshness → revalidate → `DocumentChangeCandidate` → Old/V/W → review → human commit.

`DocumentChangeCandidate` is a domain/read-model inside existing `DOCUMENT_SYNC_REVIEW`; it does not create a new canonical stage or standalone business workflow screen.

### OS-G4 — Release / Publishing

Build real release domain:
- `ReleasePlan`;
- readiness;
- exception decisions;
- exact-revision `ReleaseManifest`;
- idempotent publish;
- unknown-result recovery;
- immutable published projection.

Do not reuse legacy QC/reviewer workflow or `DocumentPackage` as a ReleaseManifest shortcut.
Accepted `DocumentRevision` is already immutable document authority; do not add a standalone `Khóa phiên bản` stage/screen. Publishing binds exact accepted revisions into the ReleaseManifest.

Supporting Phiếu KSCL as a document type does not create a KSCL workflow stage.

### OS-G5 — Template Intelligence / Fidelity expansion

After minimum deterministic document runtime exists:
- AI Template Mapper;
- advanced visual QA;
- Template Family + structural diff + mapping transfer;
- generic adaptation to new company templates;
- extended document set;
- package-part/relationship/style/numbering/media fidelity;
- dual-render conformance.

AI mapping remains proposal-only.

**OS-G5 / OS-G7 boundary:** OS-G5 may freeze AI-assisted template UX/task contracts, provider-neutral interfaces and deterministic/rule-based candidate mapping needed for template intelligence. Any LLM/external-provider execution, `AITaskRun` runtime, model routing or provider fallback is OS-G7 runtime and remains gated by the AI Master Plan unless an explicit Product Owner decision authorizes a narrower exception.

### OS-G6 — Product Completion

Complete:
- unified contextual lineage;
- cross-product states;
- Resume context;
- template/document fidelity gates;
- full exact-SHA North-star E2E;
- negative/tenant/provider-uncertain paths.

### OS-G7 — Valora Intelligence Platform & Assistant

Runtime activation remains **after the authoritative operating loop is closed**. Architecture/design may be frozen earlier so OS-G1→OS-G6 remain AI-readable-by-design without activating AI.

Master architecture: `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md`.

#### OS-G7.0 — AI Authority & Contract Freeze
Master Plan, ADR 0033/0034 reconciliation, risk taxonomy, Assistant authority, AI-readable domain contract and initial task catalog. Documentation/design only; no provider calls.

#### OS-G7.1 — AI Runtime Provenance Foundation
`AITaskRun`, append-only `AITaskAttempt`, `AIContextManifest`, `DecisionEpisode`, `RetrievalIndexRelease`; reuse compatible `LearningFeedbackEvent`; bind to existing durable `TaskJob`/worker, no second AI queue.

#### OS-G7.2 — Task Registry, Model Policy & Provider Gateway
Versioned task/input/output/prompt/schema registry, model policy, provider-neutral gateway, deterministic/mock path first, redaction/data-policy and explicit evaluated fallback.

#### OS-G7.3 — Context & Retrieval Engine
Task-specific Context Assembler, reproducible `AIContextManifest`, structured/SQL/full-text/domain retrieval first, optional embeddings as derived projections, claim-to-source citation contract and versioned retrieval releases.

#### OS-G7.4 — Valuation Knowledge v1
First bounded pack: Machinery & Equipment + Comparison Approach + Vietnam + Vietnamese; versioned methodology, evidence semantics, comparable criteria, adjustment reasoning and professional control rules.

#### OS-G7.5 — Typed Tool Registry
Tenant-safe read tools over Case State, assets, evidence, quotes, knowledge, dossiers, pricing and documents; no generic SQL/database mutation tool.

#### OS-G7.6 — Appraisal Intelligence Task Pack v1
Start with bounded R0/R1 tasks such as case summary, next-action/blocker explanation, historical asset search, evidence summary/missing detection and price-deviation explanation. AI may draft/propose; it does not approve final price.

#### OS-G7.7 — Valora Assistant
Project/case/stage/asset-aware, Vietnamese-first, Fluent 2 light, tool-enabled and citation-grounded. Conversation history is UX context, not business truth. Provider failure must leave normal VALORA workflow usable.

#### OS-G7.8 — Evaluation, Shadow & Release
Versioned evaluation corpus with leakage controls; shadow execution and independent human comparison; model/prompt/retriever regression, latency/cost and unsupported-claim/citation metrics; capability-specific release, rollback and kill switch.

#### OS-G7.9 — Controlled Automation
Promotion lifecycle: shadow → review-only → active suggestion → narrowly evaluated reversible R2. Deny-by-default `ExecutionPolicy`. R3 official mutation remains authenticated human command; R4 final price/professional approval/signature/release remains human-only.

AI never compensates for missing domain facts or missing authoritative commands.

**Cross-cutting prerequisite effective now:** every OS-G1→OS-G6 vertical slice must expose durable facts, Case State/Next Action, blocker/warning/stale semantics, evidence/lineage references and authoritative version tokens so later AI does not reverse-engineer UI state.

## 12. Mapping from the Template/Fill technical proposal

| Technical workstream | Unified placement |
|---|---|
| OfficeCLI read-only spike | OS-G3 / DOC-G1 |
| Template IR | OS-G3 / DOC-G2 |
| first report golden structural baseline | OS-G3 / DOC-G3 |
| Data Model Registry | OS-G3 / DOC-G4 |
| Template Compiler | OS-G3 / DOC-G5 |
| DOCX Fill Engine | OS-G3 / DOC-G6 |
| minimum visual QA | OS-G3 / DOC-G7 |
| AI Template Mapper | OS-G5 |
| advanced Visual QA | OS-G5 |
| Template Family / Adaptation | OS-G5 |
| OfficeCLI production mutation | future separate conformance decision; not authorized |

## 13. Immediate sequence

1. Authority + Fluent 2 light visual-system + branch closeout.
2. Pre-case product closure.
3. Appraisal Core vertical slices.
4. Start Document Runtime only when it becomes the real business critical path or a concrete earlier
   blocker proves the need.
5. Release/Publishing.
6. Template intelligence/fidelity expansion.
7. Full product E2E.
8. Valora Intelligence Platform & Assistant — execute OS-G7.0→OS-G7.9 only under explicit gates; provider/runtime activation remains downstream of authoritative-loop completion.

## 14. Governing principles

> VALORA must complete the business operating loop before optimizing platform sophistication.

> DocumentRevision means that VALORA has officially accepted a document version.

> AI, Office tools, Word and OneDrive may observe, analyze, render or recommend, but authoritative
> mutation always passes a domain-controlled, human-confirmed boundary.

> Template intelligence serves Appraisal OS; Appraisal OS must not become an Office-platform project.

> UI/UX Handoff v2.3 defines product semantics and visual authority; this roadmap sequences implementation and must not silently redesign the product.
