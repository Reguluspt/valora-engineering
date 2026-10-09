# Valora test-design guard proposal

**DRAFT / NOT ACTIVE — PM-OPS-005-03 / [Issue #172](https://github.com/Reguluspt/valora-engineering/issues/172), 2026-10-10.** This document proposes a future manual procedure and command surface. It installs no skill, changes no SOP/CODEX, test or CI policy, and authorizes no test removal. Certification of this document would not activate the proposal. Product Owner (PO) adoption remains a separate decision.

## Evidence and authority

| Source | Exact checkpoint and implication |
| --- | --- |
| [Official handoff](https://github.com/Reguluspt/valora-engineering/issues/172#issuecomment-6086093476) | One new document only; downstream adoption risk HIGH; native independent DeepSeek/Gemini review required. |
| Authorized main | `b482c999d17a983af3ae99e16026e4261e862a27`; CODEX blob `de7e47d224a4f90bc190c182638d6a55c17540e5`. [CI #662](https://github.com/Reguluspt/valora-engineering/actions/runs/37962101954), push, completed SUCCESS, five individual successes. |
| [#167 certified baseline](VALORA_PM_OPS_005_TEST_CI_BASELINE_REPORT.md) | Blob `ff901ffec446e30e79959c34a2ed263f6ac8ab94`; [certification](https://github.com/Reguluspt/valora-engineering/issues/167#issuecomment-6082367434), CLOSED. Backend pytest dominates the historical CI sample; this does not identify expensive individual tests. |
| [#168 certified audit](VALORA_PM_OPS_005_BEHAVIORAL_TEST_QUALITY_AUDIT.md) | Blob `4c1b1c948c827a4d3ddfdcf67b42f83773240ff1`; [certification](https://github.com/Reguluspt/valora-engineering/issues/168#issuecomment-6085991696), CLOSED. 30 groups: 26 KEEP, 2 STRENGTHEN-LATER, 2 INVESTIGATE; ZERO justified MERGE/REMOVE. |
| Existing operating authority | [CODEX §§1, 8.1, 10](../../CODEX.md#81-exact-head-baseline-and-dependent-task-gate), [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md), [Operating Protocol v2](VALORA_AGENT_OPERATING_PROTOCOL_V2.md). Existing authority wins over this draft. |
| Protected domain | [ADR 0026](../adr/0026-authentication-identity-boundary-hardening-proposal.md), [ADR 0028](../adr/0028-official-mutation-command-and-atomic-audit-gate.md), [ADR 0043](../adr/0043-app-owned-immutable-document-storage.md), [ADR 0045](../adr/0045-working-copy-change-observation-and-human-confirmed-document-revision.md), [A13](../implementation/VALORA_OS_G2_SUPPLIER_QUOTES_RUNTIME.md#verification-and-boundaries), [A14](../implementation/VALORA_OS_G2_SUPPLIER_QUOTES_PRODUCT.md#authority-and-product-surface). Product runtime remains SUPPLIER_QUOTES. |

Source anchors below refer to the authorized main tree; symbolic test names identify cases where parameter-expanded node IDs were not measured. Per-test/fixture timings, billed cost, actual runner/test/token savings, dynamic mutation sensitivity and complete Linux/Windows node-ID parity are **NOT MEASURED**. Historical aggregate timing does not establish optimization benefit.

Goal: independently detect relevant regressions with the smallest reliable coverage addition. Coverage count and CI speed are subordinate to preserved business/security/UX fault detection. A manual card may be sufficient; automation must demonstrate added value before adoption.

## Proposed test-intent card

Every future proposal would fill this card before writing a test. A missing contract/oracle is INVESTIGATE, not permission to invent expected behavior.

| Required field | Reviewable answer |
| --- | --- |
| Changed production behavior | Exact production path/symbol, old/new observable behavior, approved contract section and source SHA. For an existing gap, say no production change and cite the existing accepted behavior. |
| Plausible independent defect | A specific implementation error and reachable trigger; describe the wrong business/security/UX outcome without deriving it from the implementation's own return value. |
| Existing coverage | Exact test IDs/assertions and relevant fixtures; state what they already detect and the defect that escapes. Similar names/setup alone are insufficient. |
| Independent oracle | Explicit expected response, rendered output, literal exact Decimal, persisted before/after facts, rollback, absence of forbidden writes or separately observed bytes. Identify provenance; never compute the expected value by calling the same production helper being tested. |
| Lowest reliable layer | Unit → component → integration/service+DB → API/contract → E2E. Choose the first layer that observes the actual defect, not merely its proxy. Explain why cheaper layers fail; retain higher-layer tests with distinct transport, DB, browser or native failures. |
| Mock/golden provenance | Contract-authored literals or separately verified protocol/example; mocked boundary and excluded behavior; golden origin/version/independent compatibility oracle. Self-generated snapshots are not independent truth. |
| Positive, negative and boundary paths | Valid control, invalid/stale/cross-scope input and meaningful boundary; precise deterministic expected outcomes. Specify clock, random identity, concurrency coordination and environment without arbitrary sleeps. |
| Blast radius and existing suites | Direct owners, transitive consumers, protected crosscuts, platform/service prerequisites and existing required gates. Unknown dependency means full gate and investigation. |
| Decision and cost evidence | **NEW TEST / EXTEND EXISTING / NO NEW TEST** and reason. Name one defect not already caught for NEW; prefer EXTEND for the same behavior/oracle. Record measured incremental cost or NOT MEASURED, never assume short equals cheap. |
| Evidence/owner | Source/test anchors, evidence confidence, missing facts, proposed controlled fault proof, responsible domain/test owner and required approval. A card is not proof of measured sensitivity. |

Anti-explosion acceptance: each NEW proposal must identify unique fault detection, a lower-cost valid layer comparison, positive/negative cases and deterministic pass/fail criteria. Parameterization is appropriate when it preserves each distinct boundary and diagnostic identity. NO NEW TEST is legitimate when existing coverage independently detects the changed behavior. No percentage quotas, test-count targets or delete-first budgets.

## Proposed failure investigation protocol

Before changing a failed test **or production code**, preserve the original failure: exact SHA/run/job/test ID, environment, assertion/expected/actual, reproduction and test/domain owner. Inspect the accepted contract, changed code, fixture and relevant history. Determine whether the failure is a real regression, stale expectation following an approved contract change, fixture defect, environment mismatch, infrastructure failure, flaky behavior or UNKNOWN. A retry alone does not classify a failure; preserve unsuccessful attempts.

Use [the existing CI failure taxonomy](VALORA_AGENT_OPERATING_PROTOCOL_V2.md#ci-failure-taxonomy) for rerun authority. UNKNOWN stays blocked. Reproduce at the cheapest faithful layer and identify a causal fault and independent oracle; escalate ambiguous audit/tenant/RBAC/CAS/domain authority to Gate Owner before edits. A valid regression needs an authorized production fix; a stale test needs the accepted contract change plus replacement fault coverage. Changes outside the current task require a separate task.

Never comment out tests, add skip/xfail/quarantine, regenerate snapshots, increase timeouts arbitrarily, weaken assertions or bypass CI solely to turn it green. An exception needs separate advance PO approval, recorded reason, replacement-coverage evidence and a bounded restoration/verification plan; Dev/Codex cannot approve itself. Even an approved exception cannot be represented as a passed test or waive the governing exact-head gate. Intentional prerequisite/platform skips must retain their reason and require the appropriate environment proof.

## Traceable audit rubric and recommendation thresholds

This is a proposed human rubric, **not an installed detector**. Score each dimension separately: `0` missing/unsupported, `1` source-supported with runtime/provenance limits, `2` independently evidenced by contract and observed fault/control proof. Record evidence beside every score; `2` fault sensitivity requires an actual controlled experiment under separate authorization. Static plausibility alone earns at most `1` for sensitivity.

Dimensions: **A** accepted behavior/authority; **O** independent observable oracle; **F** plausible defect and fault sensitivity; **D** distinctness or replacement equivalence versus named existing cases; **E** deterministic environment/platform and fixture/golden provenance. No total-score cutoff can override a missing safety fact; record measured cost separately, never reward speed over protection. Existing source-supported tests remain KEEP pending measurement rather than being deleted for a low score.

| Recommendation | Minimum evidence and resulting action |
| --- | --- |
| KEEP | Accepted protected behavior and a source-supported independent observable failure detector; identify its unique layer/fault and environment. Runtime sensitivity may remain unmeasured and must be labeled. Uncertainty about overlap defaults to retention. |
| STRENGTHEN-LATER | Exact assertion and concrete escaping defect; accepted target behavior/oracle and plausible stronger assertion at the lowest reliable layer. Retain existing useful assertions. Unresolved target authority adds INVESTIGATE and blocks implementation. |
| INVESTIGATE | Missing/ambiguous invariant, oracle, platform proof, fixture provenance, overlap or timings. Name the unanswered question, owner and smallest evidence-gathering step. No mutation/removal until resolved. |
| Potential MERGE | Independently observed old-test fault matrix and replacement detection for **every** old positive/negative/boundary case, with reproducible setup, equivalent platform/role/DB/transport behavior and preserved diagnosability/isolation. A/O/F/D/E must all be `2` for the affected replacement claim; measure before/after setup/execution in matched environments if claiming benefit. A hypothesis remains INVESTIGATE. Separate authorized implementation and independent reviewers are required. |
| Potential REMOVE | Either separately accepted retirement of the behavior with transitive consumer/protection review, or proven surviving coverage for every removed failure class under the same MERGE standard. No unowned protected invariant or unique platform/layer detector may disappear. Explicit PO authorization and independently reviewed proof precede execution; removal never follows from length, green CI, score total or shared fixtures alone. |

Flag `true == true`, a mock compared to the same mock, an empty assertion path, implementation-generated expected output, stale/unreviewed snapshots, duplicate observable detectors and unexplained skips. For each flag name exact source/test/assertion, the defect that escapes and surviving value. Short tests can enforce critical boundaries; POSIX-only tests can be essential. Similar assertions at different layers can catch independent faults; a source flag is not a removal verdict. Goldens can preserve a wire contract when independently pinned and paired with behavioral checks; do not regenerate them merely after a failure.

## Three grounded, self-contained example cards

### B25 — extend presentation coverage, retain write locks

Source: [`SupplierQuotesRegion.test.tsx`, `presents server %s...`](../../frontend/src/components/workbench/supplier-quotes/__tests__/SupplierQuotesRegion.test.tsx#L42-L46). The test sets `snapshot.result = result`, then asserts `m.quotes.snapshot?.result` equals that same value. This self-echo would pass if [`SupplierQuotesRegion`](../../frontend/src/components/workbench/supplier-quotes/SupplierQuotesRegion.tsx) rendered COMPLETE for every result. The same case independently checks missing confirmation/registration buttons: retain it.

| Card | Proposed answer |
| --- | --- |
| Behavior/authority | No production change in #172. A14 requires display of the server's five quotation results, without frontend completion derivation. |
| Fault and oracle | Renderer hardcodes COMPLETE or drops STALE. Inspect rendered status text with a contract-reviewed literal table: NOT_AVAILABLE → `Chưa khả dụng`; BLOCKED → `Đang bị chặn`; STALE → `Cần xem lại`; INCOMPLETE → `Chưa hoàn tất`; COMPLETE → `Hoàn tất`. Read rendered badge output; do not import `CASE_RESULT_LABELS` to calculate expected labels using the renderer's own mapping. The existing [presentation labels](../../frontend/src/components/case-overview/caseOverviewPresentation.ts#L28-L36) are source corroboration, not independent expected-value generation. |
| Coverage/layer | B24 API payload and `useSupplierQuotes` hook result tests cannot detect a renderer ignoring the result. EXTEND EXISTING parameterized component case; no new API/E2E case merely to recheck the label. Preserve absent write buttons when `writable/enabled` are false, including COMPLETE. |
| Controls/provenance | Five explicit server-result fixture variants; positive COMPLETE display and negative STALE/BLOCKED display; literal labels reviewed against A14's Vietnamese presentation requirement. Fluent mock limits styling/accessibility/browser claims. Distinguish badge text from unrelated history/status copy. |
| Future proof/gates | In a separately authorized test task, temporarily hardcode the rendered result in an isolated disposable copy: the new assertion must fail while the old self-echo still passes. Restore the fault; verify all five controls pass and write-lock assertions remain. Frontend affected regressions and full five-job exact-head CI remain required. No fault experiment or measured sensitivity performed here. |
| Disposition | STRENGTHEN-LATER / EXTEND EXISTING; no deletion and cost NOT MEASURED. |

### B05 — investigate the enforcement boundary before a DB invariant

Source: [`test_audit_event_append_only_policy`](../../backend/tests/test_audit_event_foundation.py#L138) checks absence of `update_audit_event` / `delete_audit_event` exports. A differently named writer or direct SQL could rewrite rows and still pass. [`test_log_audit_event_transactional`](../../backend/tests/test_audit_event_foundation.py#L73-L103) independently proves rollback/transaction ownership, not DB-role immutability.

The [guardrails](../../ENGINEERING_GUARDRAILS.md#5-security-guardrails) require append-only audit logs, but do not by themselves establish universal DB-trigger denial for every maintenance role. [`test_latest_cycle_fault_cannot_reuse_historical_grant_provenance`](../../backend/tests/test_g2_a5r2_workbench_open_rbac_postgresql.py#L277-L304) deliberately UPDATEs/DELETEs audit records as isolated fault injection. This does not authorize production tampering or disprove application append-only intent; it requires reconciling role privileges and the intended enforcement layer.

| Card | Proposed answer |
| --- | --- |
| Behavior/authority | No changed production behavior. Gate Owner/domain owner must resolve application-command versus DB-role immutability, including migration/maintenance exceptions, table scope and accepted failure semantics. Do not invent a universal trigger requirement. |
| Plausible fault | An authorized runtime principal can rewrite/delete committed audit evidence without detection. Existing helper-name assertion would miss the fault. |
| Conditional independent oracle | **Only if the accepted contract requires DB-level enforcement:** append a synthetic row using the real runtime DB role; attempt separate UPDATE and DELETE; observe required rejection and unchanged row/content/count through a fresh transaction/connection. Positive authorized append must still work. Do not accidentally use a privileged migration owner as the runtime principal or mistake broken SQL/aborted transaction for enforcement. |
| Coverage/layer | Real PostgreSQL role/transaction integration is the cheapest reliable layer for a DB privilege/trigger requirement. B04's rollback and B13's quotation-table constraints do not prove global audit enforcement. If authority chooses an application boundary instead, design its command-level oracle rather than imposing DB DDL. |
| Decision/proof | INVESTIGATE invariant first; STRENGTHEN-LATER for the known assertion gap. NO NEW TEST until authority is resolved, then NEW or EXTEND based on the named existing role-aware coverage. Future fault proof must demonstrate that an authorized loss of enforcement makes the invariant test fail. No DB change/test or experiment authorized here. |
| Blast radius | Backend, worker, migrations, audit consumers and shared command contracts; full protected crosscut gate. Retain B04, B05 and grant-provenance coverage; no removal recommendation or measured savings. |

### B19 / 21 POSIX-only local blob tests — KEEP platform safety coverage

Source: [`test_document_blob_store_local.py:22–27`](../../backend/tests/test_document_blob_store_local.py#L22-L27) intentionally skips the module without POSIX/hard links and explicitly says a skip is not PASS. There are 21 top-level test functions, including async functions. #167's Windows collection 2,310 plus 21 numerically reconciles Linux 2,331 passed; this is **not** direct node-ID parity or a new candidate execution result.

| Card | Proposed answer |
| --- | --- |
| Behavior/authority | ADR 0043 local immutable bytes and root confinement; no production change. Preserve environment-specific hard-link publication, crash/race and cleanup behavior. |
| Concrete failure/oracle | [`test_l14_concurrent_different_content_never_overwrites_winner`](../../backend/tests/test_document_blob_store_local.py#L790-L855): an overwrite race admits two writers or corrupts the winner. Independent observations are exactly one CREATED and one REJECTED, physical final bytes equal to the winning input, checksum match and empty staging. The test's barrier coordinates the race; arbitrary sleeps are not equivalent. |
| Negative boundary | [`test_l11_path_traversal_absolute_backslash_and_control_input_rejected`](../../backend/tests/test_document_blob_store_local.py#L626-L683) denies escaping/invalid object keys. Root and retained byte outcomes are observable security facts. |
| Existing coverage/layer | S3 conditional writes test a different provider protocol; mocks/Windows collection cannot establish POSIX atomic filesystem behavior. Lowest reliable layer is Linux/POSIX filesystem integration with temporary roots and actual hard links. |
| Decision/proof/gates | KEEP all 21, NO NEW TEST for this proposal. Before any future change, preserve module/function inventory and confirm platform-appropriate execution without hidden skips. Optional separately authorized race/path fault injection could measure sensitivity; it has not run here. Backend full Linux CI remains mandatory; non-POSIX skip is a limitation, never redundancy or PASS. |

## Proposed future commands and manual prompts

**Not installed or executable Valora capability.** Any third-party article's test-agent/optimization concept is inspiration only: it is not an accepted Valora rule, a detector or evidence of installed commands. No external article is adopted by this proposal.

| Proposed surface | Future semantics after separate adoption; default output only |
| --- | --- |
| `/valora:test create <change>` | Read accepted behavior and affected sources, inspect coverage, fill the intent card and recommend NEW/EXTEND/NONE. Produce a reviewable test plan; writing tests requires a task explicitly allowing exact test paths. No implicit generation or runtime mutation. |
| `/valora:test audit <scope>` | Read exact source at a pinned SHA; report rubric evidence and KEEP/STRENGTHEN-LATER/INVESTIGATE/candidate recommendations. Read-only; source flags do not prove dynamic sensitivity. |
| `/valora:test optimize <scope>` | Read-only candidate analysis using matched per-test/setup/teardown timings, existing fault coverage and separately accepted shadow blast-radius evidence. Without timings or shadow proof, return INVESTIGATE / insufficient evidence. No deletion, merges, fixture rewrites, selective runs or CI mutation by this command. |
| Optional `--ultra` | Future deeper research plan only: list unanswered questions, proposed experiments, scope and explicit provider/cost approvals needed. Never silently call five paid agents, install tooling, select another model or mutate CI. No paid probe dispatched by default. |

Manual fragments: `Create: At <SHA>, compare <approved behavior> with <existing test IDs>; name one escaping defect, independent oracle and lowest reliable layer; recommend NEW/EXTEND/NONE.` `Audit: Trace <scope> to accepted contracts; retain protected detectors; report exact escaping defects and missing evidence.` `Optimize: Show matched timing provenance and old/replacement fault matrix; absent proof, INVESTIGATE; propose no executable CI change.`

Future evaluation would use a PO-approved bounded corpus of changed behaviors, unique protected tests, tautological sub-assertions and apparent duplicates. Record correct recommendations, false removal/merge recommendations, oracle provenance, independently reproduced fault/control outcomes and reviewer disagreement per case, not a blanket coverage percentage. Required acceptance: zero protected detectors lost, zero unsupported removal/merge or authority invention, all proposed NEW cases satisfy the card, B25 identifies rendered output, B05 holds for authority, all 21 POSIX cases retained. Record elapsed author/reviewer effort and matched test/setup/teardown distributions before/after any separately authorized implementation; report raw measurements and uncertainty. Billing remains unknown unless billing evidence is supplied. PO sets the corpus and success criteria before evaluation; no GO is inferred from this draft.

## Blast-radius proposal and preserved CI gates

Map changed paths to owners, then follow imports, shared fixtures, API/schema consumers, migration effects, provider contracts, native bridges and process-authority consumers. Record why each lane is affected or apparently unaffected. Filename/path alone cannot certify a safe exclusion.

| Potential affected lane | Dependency examples; this is advisory mapping, not selective-CI activation |
| --- | --- |
| Backend | `backend/**`; services/DB/API, tenant/RBAC/auth/audit/CAS, storage, migrations and shared contracts; include worker and frontend/native consumers where relevant. |
| Frontend | `frontend/**`; adapters, renderer and shared UI; backend contract changes and browser/native bridge consumers can affect it transitively. |
| Worker | `worker/**` and imported backend jobs/models/config; lease/retry/audit and storage/provider changes can cross lanes. |
| Server-foundation | `infra/server/**`, deployment topology, TLS/header trust, secrets/provider configuration and shared backend/worker assumptions. |
| Committed-whitespace | Every committed source/document change, including this proposal. |
| Windows Client | `clients/windows/**`, origin/session/bridge contracts, server/frontend compatibility. No Windows Client job exists in the current five-job workflow; require separately authorized applicable native proof, never invent a sixth current check or count CI as native coverage. |

Unknown dependencies, tenant/RBAC/auth/audit/CAS/migrations/security/shared contracts/CASE_STATE/SUPPLIER_QUOTES fail **CLOSED** for any future exclusion: retain full gates and seek the missing evidence. Tests spanning different layers remain until equivalent fault detection is proven. Even a docs-only change to a governing contract can affect all consumers.

The existing [CI workflow](../../.github/workflows/ci.yml) remains unchanged. **Backend, frontend, worker, server-foundation and committed-whitespace all remain mandatory**, each completed SUCCESS on the frozen exact candidate; post-merge the same five must succeed on the exact resulting main. No green inheritance, skipped-job substitution, path-filter change, required-check/ruleset change or semantic certification of future commands from these jobs. Changing HEAD invalidates prior candidate reviews and CI. #005-04 shadow design is a separate unopened task; any future classifier must compare proposed selections to full-gate outcomes and fault-detection/coverage evidence, including protected/unknown crosscuts, under a PO-approved corpus. #005-05 workflow adoption and #005-06 rollout need separate explicit PO decisions after accepted shadow proof. This task starts none of them.

## Approval and delivery boundary

| Decision | Authority and evidence needed; no automatic promotion |
| --- | --- |
| Accept/revise/reject this draft | Gate Owner inspects one frozen candidate, complete independent native DeepSeek/Gemini HIGH reports, adjudicated findings and exact-head five-job CI. PO retains adoption GO / REVISE / NO-GO. |
| Install skill / activate command | Separate explicit PO task and bounded install paths, accepted behavior and measured evaluation; review actual installed content and privacy/provider controls. |
| Change CODEX / SOP | Separate PO policy approval, named authority reconciliation and reviewed exact-head gates. Proposal certification does not amend policy. |
| Strengthen/merge/remove test or fixture | Separate exact-path task, resolved domain authority, intent/fault/replacement evidence and risk-appropriate independent review; preserve protected cases and platform proofs. |
| Change workflows / required checks / branch rules | Separate explicit PO decision following accepted #005-04/#005-05 shadow evidence; preserve protected full exact-head/main gate requirements. |
| Ready / merge / certification / closure | ChatGPT Gate Owner only; expected-head guarded integration and exact-main post-merge five-job certification. #172 delivery is Draft PR `Refs #172`. |

Local document checks for this candidate: T0 validates prerequisite report blobs, counts, exact anchors and card completeness; T1 traces the three examples to tests, implementation and accepted authority and challenges each fault/oracle; T2 checks links, one-new-file diff, whitespace, secrets/privacy and no protected-source changes. T3 runtime/PostgreSQL/browser is N/A under the docs-only contract; no unnecessary full backend local suite. Local check results, frozen SHA, native reviewer identity/terminal/isolation receipts, findings and exact-head CI belong in external candidate evidence, not self-referential claims inside this source document. An unavailable/incomplete native reviewer leaves readiness NO; do not substitute a model or blindly repeat a length-ended attempt.

Principal adoption risks: a rubric could reward assertion count instead of observable defects; lowest-layer preference could erase genuine DB/transport/native failures; apparent duplicates could conceal different protected oracles; hardcoded labels could drift without contract review; command automation could silently turn recommendations into writes. The counterweight is manual, source-traced evidence, retained unique detectors, explicit authorization and a bounded evaluation before any install. Keep the manual procedure or reject automation if it adds review burden without demonstrated fault-detection value.

**DRAFT / NOT ACTIVE.** No skill install, SOP/CODEX activation, test modification/removal/skip, CI selection, paid research workflow or downstream runtime is authorized by this document. OpenViking remains optional, manual and non-authoritative under VALORA_LEAN_MCP; automatic injection/recall/capture stays off. No cost or time saving is claimed.
