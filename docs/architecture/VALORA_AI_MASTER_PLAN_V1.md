# VALORA AI MASTER PLAN v1.0
## Nền tảng Trí tuệ Thẩm định & Trợ lý Valora

**Status:** CURRENT OS-G7 ARCHITECTURE DETAIL / DOCUMENTATION AUTHORITY — DOCUMENTATION ONLY<br>
**Date:** 2026-09-23<br>
**Product authority:** VALORA Appraisal OS v2.3<br>
**Code baseline reviewed:** `feat/operational-frontend-m365`<br>
**Exact HEAD:** `d725bbc6f60f2a21ec11a555d9565d2ab01470ae`<br>
**Exact-head CI:** `#454 — SUCCESS`<br>
**Runtime authorization:** NONE. Tài liệu này không kích hoạt provider AI, migration AI, autonomous command hay thay đổi human approval gate.

## 1. Quyết định định hướng

VALORA sẽ tiến hóa thành một **AI-native Appraisal Operating System**, nhưng AI không được trở thành nguồn sự thật nghiệp vụ song song.

```text
Authoritative VALORA Domain
        ↓
Context + Retrieval + Tools
        ↓
Valora Intelligence Platform
        ↓
Valora Assistant
        ↓
Observation / Explanation / Proposal
        ↓
ExecutionPolicy
        ↓
Human-controlled Domain Command
        ↓
Authoritative VALORA Domain
```

> **VALORA sở hữu dữ kiện, workflow, thẩm quyền tri thức và các quyết định chuyên môn. AI chỉ là nhà cung cấp năng lực suy luận có thể thay thế.**

AI có thể truy xuất, phân tích, giải thích, so sánh, phát hiện, soạn thảo và đề xuất. AI không được âm thầm biến suy luận của chính nó thành sự thật thẩm định có thẩm quyền.

## 2. Kết quả kiểm tra exact-head

OS-G0 đã tiến triển qua F2-PR-001, F2-PR-002 và F2-PR-003 trên integration branch. PR #38 đã thay Astryx production shell bằng semantic React/HTML + Fluent 2 light primitives và bổ sung các primitive trạng thái dùng chung như `MessageBar` và `StateSurface`.

Nền tảng có thể tái sử dụng cho AI đã tồn tại:
- tenant/RBAC/security boundaries;
- security audit primitives;
- Evidence domain;
- Technical Specification;
- `KnowledgeVersion`;
- `AppraisedPriceDecision`;
- Column Mapping Memory foundations;
- Asset Identity Decision;
- `LearningFeedbackEvent`;
- dossier source/extraction foundations;
- `TaskJob`, `TaskJobAttempt`, lease/fencing/retry/dead-letter;
- reliable worker;
- Global Case State foundation cho bốn canonical stages đầu tiên.

Chưa có runtime implementation của `AITaskRun`, `AITaskAttempt`, `AIContextManifest`, `DecisionEpisode`, `ExecutionPolicy`, Provider Gateway/Task Registry và Valora Assistant.

**Quyết định tái sử dụng:** AI phải dùng chung durable `TaskJob`/worker. Không tạo AI-specific queue thứ hai.

## 3. Authority và tài liệu nền

Tài liệu này carry-forward các quyết định đúng từ ADR 0033, ADR 0034, các phần AI/knowledge/memory của Design Book v1.4 chưa bị supersede, và historical S13–S16 như implementation evidence. Unified Roadmap v2.3 tiếp tục quyết định thứ tự phát triển. Master Plan này chi tiết hóa OS-G7, không kéo runtime AI lên trước authoritative operating loop.

## 4. Kiến trúc đích

```text
Authoritative Domain Truth
        │
        ├── Case State + Next Action
        ├── Knowledge Registry
        └── Evidence + Lineage
                 │
                 ▼
        VALORA CONTEXT ENGINE
                 │
          AIContextManifest
          ┌──────┴──────┐
          ▼             ▼
   Retrieval Engine   Tool Registry
          └──────┬──────┘
                 ▼
          AI Task Registry
                 ▼
            Model Policy
                 ▼
        AI Provider Gateway
                 ▼
             AITaskRun
                 ▼
        Structured Result
          ┌──────┴──────┐
          ▼             ▼
     Explanation   ActionProposal
                        ▼
                 ExecutionPolicy
                        ▼
                 Human/domain gate
                        ▼
                  Domain Command
                        ▼
                 DecisionEpisode
                        ▼
              LearningFeedbackEvent
```

## 5. Invariant: AI-readable-by-design

Từ OS-G1 đến OS-G6, mỗi authoritative business slice phải đủ sạch để AI đọc sau này mà không reverse-engineer UI/database.

Mỗi canonical stage nên expose bounded read model có tối thiểu:

```text
stage
facts
warnings
blockers
stale conditions
next actions
evidence references
lineage references
allowed human commands
authoritative version tokens
```

Đây là domain/read-model contract, chưa phải AI API.

## 6. Case State là orchestration truth

Assistant không tự suy diễn lifecycle state từ hội thoại. Nó đọc Global Case State và authoritative projections. Hiện exact-head mới có provider cho bốn stage đầu; stages 5–16 phải được đóng theo roadmap trước khi AI reasoning end-to-end trên toàn hồ sơ.

## 7. Valuation Knowledge Layer

Bổ sung `ValuationKnowledgePack` với scope v1:
- Domain: Machinery & Equipment;
- Method: Comparison Approach;
- Jurisdiction: Vietnam;
- Language: Vietnamese;
- Status: versioned/reviewed/active.

Pack phải phân biệt:
1. method rules;
2. evidence policy;
3. adjustment reasoning;
4. professional warning/blocker/rationale/minimum-evidence rules.

Knowledge chuyên môn phải versioned/reviewed; không giấu trong system prompt.

## 8. AI Context Engine

Mỗi registered task đi qua Task → Context Policy → Authorized sources → Transform/redact/summarize → `AIContextManifest`.

Manifest ghi reference/hash/version/bounded summary của đúng context đã cấp cho model, phục vụ audit, reproducibility, tenant isolation, stale detection, privacy và evaluation.

## 9. Retrieval architecture

Ưu tiên:
```text
authoritative direct lookup
→ structured filtering
→ SQL/full-text search
→ domain similarity
→ embedding/vector retrieval where useful
→ AI rerank where useful
```

Embeddings/vector indexes là derived projections. `RetrievalIndexRelease` phải biết source dataset, normalization, embedding, retriever và evaluation release versions.

## 10. Citation architecture

Material factual claim của Assistant phải resolve được về nguồn.

```text
AssistantResponse
├── answer
├── claims[] → claim + source_refs[]
├── warnings[]
├── proposed_actions[]
└── provenance
```

Source refs có thể trỏ tới EvidenceFile/EvidenceSource/QuoteLine/KnowledgeVersion/Historical Dossier/DocumentRevision/page-table-row-cell locator/domain decision.

## 11. AI Task Registry

Không có generic business endpoint kiểu `POST /ai/chat` để reasoning tùy ý. Mỗi task đăng ký task/version/risk/input/output/context/tools/model/fallback/timeout/budget/evaluation release. Unregistered task/model/provider/tool fail closed.

## 12. Appraisal AI Task Catalog v1

**Case R0:** `CASE-SUMMARY`, `CASE-STATE-EXPLAIN`, `NEXT-ACTION-EXPLAIN`, `BLOCKER-EXPLAIN`, `CASE-MISSING-INPUT-DETECT`.

**Asset R0/R1:** `ASSET-NORMALIZE-SUGGEST`, `ASSET-IDENTITY-RERANK`, `ASSET-SIMILARITY-EXPLAIN`, `ASSET-MISSING-SPEC-DETECT`, `HISTORICAL-ASSET-SEARCH`.

**Evidence R0/R1:** `EVIDENCE-SUMMARIZE`, `EVIDENCE-QUALITY-REVIEW`, `EVIDENCE-CONFLICT-DETECT`, `EVIDENCE-MISSING-DETECT`, `SOURCE-FRESHNESS-EXPLAIN`.

**Comparable R1:** `COMPARABLE-SEARCH`, `COMPARABLE-RANK`, `COMPARABLE-DIFFERENCE-EXPLAIN`, `COMPARABLE-RATIONALE-DRAFT`.

**Pricing R0/R1:** `PRICE-RANGE-ANALYZE`, `PRICE-OUTLIER-DETECT`, `PRICE-DEVIATION-EXPLAIN`, `PRICE-EVIDENCE-SUMMARY`, `APPRAISAL-RATIONALE-DRAFT`.

**Document R0/R1:** `REPORT-CONSISTENCY-CHECK`, `DOCUMENT-MISSING-DATA-DETECT`, `REPORT-RATIONALE-DRAFT`, `DOCUMENT-EVIDENCE-CROSSCHECK`.

AI không commit final appraised price.

## 13. Tool Registry

Read tools trước: case, asset, evidence, supplier quotes, knowledge, dossier, pricing, document. Cấm generic `execute_sql`, `update_record`, `set_final_price`, `publish`.

## 14. ActionProposal & ExecutionPolicy

Write-capable suggestion phải thành typed `ActionProposal`, sau đó đi qua deterministic/versioned `ExecutionPolicy` kiểm tra tenant, RBAC, workflow state, expected version, evidence completeness, risk tier, capability release, task/model release và reversibility. Unknown context/action => review/blocked.

## 15. Risk model

| Tier | Ý nghĩa | AI authority |
|---|---|---|
| R0 | read/retrieve/explain | có thể tự động trong data policy |
| R1 | suggest/classify/draft | proposal tự động, human giữ authority |
| R2 | reversible staging | chỉ sau task-specific evaluated promotion |
| R3 | official mutation | authenticated human command |
| R4 | professional approval | luôn human; automation prohibited |

R4 gồm final appraisal price, professional approval, signature, official report acceptance và release/publication.

## 16. Valora Assistant

`AssistantSession` scope theo organization, authenticated user, project/case, current UI route và current asset/document nếu có. Conversation history chỉ là UX context; không tự trở thành business knowledge, learning feedback, organization policy hay professional decision.

Assistant UX phải Vietnamese-first, Fluent 2 light, project-aware, stage-aware, asset-aware, tool-enabled và citation-grounded.

## 17. Model architecture

Feature code không gọi provider trực tiếp:

```text
AITask → ModelPolicy → ProviderGateway
```

Multi-model chỉ thêm khi evaluation chứng minh giá trị. Open-ended multi-agent không phải dependency của OS-G7 v1.

## 18. Durable execution

AI reuse `TaskJob`, `TaskJobAttempt`, `ReliableJobWorker`; không tạo queue riêng. AITaskRun liên kết durable job và tôn trọng idempotency, lease, heartbeat, generation fencing, retry, timeout, dead-letter và stale-result rejection.

## 19. Provenance & learning

Mỗi provider execution ghi task/context/prompt/schema/retriever/provider/model/release/latency/cost/result/error/fallback.

Learning chain:
```text
AI Proposal
→ Human review
→ Committed domain decision
→ DecisionEpisode
→ LearningFeedbackEvent
→ Derived retrieval projection
```

Không lấy positive learning từ UI click, autosave, failed/unreviewed/stale/superseded AI output hoặc conversation text đơn thuần.

## 20. Ranh giới OS-G5 Template Intelligence và OS-G7 AI Runtime

OS-G5 được phép hoàn thiện UX/domain contract cho AI-assisted template setup, provider-neutral task/interface contracts và deterministic/rule-based candidate mapping sau khi deterministic Document Runtime tối thiểu tồn tại.

OS-G5 **không tự cấp quyền** cho LLM/external-provider execution. Mọi provider-backed template analysis/mapping, model routing, `AITaskRun` execution và provider fallback vẫn thuộc OS-G7 runtime, trừ khi Product Owner có quyết định explicit mở một exception hẹp với task-specific contract/evaluation gate.

Điều này giữ nguyên Design Authority của các AI Template baselines mà không phá sequencing nguyên tắc “authoritative operating loop first”.

## 21. OS-G7 execution gates

- **OS-G7.0:** AI Authority & Contract Freeze — docs/design only.
- **OS-G7.1:** AI Runtime Provenance Foundation.
- **OS-G7.2:** Task Registry, Model Policy & Provider Gateway.
- **OS-G7.3:** Context & Retrieval Engine.
- **OS-G7.4:** Valuation Knowledge v1.
- **OS-G7.5:** Typed Tool Registry.
- **OS-G7.6:** Appraisal Intelligence Task Pack v1.
- **OS-G7.7:** Valora Assistant.
- **OS-G7.8:** Evaluation, Shadow & Release.
- **OS-G7.9:** Controlled Automation.

## 22. PR program

| PR | Scope | Runtime authorization |
|---|---|---|
| AI-PR-000 | Master Plan + authority reconciliation | docs-only |
| AI-PR-001 | AI provenance models/migrations | gated |
| AI-PR-002 | Task Registry + deterministic/mock Gateway | gated |
| AI-PR-003 | Context Assembler + AIContextManifest | gated |
| AI-PR-004 | Retrieval + source/citation contract | gated |
| AI-PR-005 | Valuation Knowledge Pack v1 | gated |
| AI-PR-006 | Typed read Tool Registry | gated |
| AI-PR-007 | First R0 Appraisal Tasks | gated |
| AI-PR-008 | Valora Assistant shell/UX | gated |
| AI-PR-009 | First real provider/model adapter | gated + explicit provider authorization |
| AI-PR-010 | Shadow/evaluation harness | gated |
| AI-PR-011 | Model/Prompt/Retriever Release Registry | gated |
| AI-PR-012 | Selected R1 production tasks | gated + task-specific release |

## 23. Điều phải làm trong OS-G1 → OS-G6

Mỗi stage mới phải có durable facts, API, UI, Case State, Next Action, blocker/warning/stale semantics, lineage, evidence refs và version tokens.

## 24. Production safety invariants

Không cross-tenant retrieval; provider không có DB session; model không trực tiếp persistence mutation; unregistered task/tool/model/provider bị từ chối; không autonomous R3/R4; material claims truy nguồn được; provider failure giữ manual path; stale result không tác động generation mới; promoted capability có rollback/kill switch; provenance tái tạo được release/input.

## 25. Explicit non-goals

Không general autonomous agent, AI final-price approval, AI signature, AI release/publishing authority, self-modifying prompt/policy, per-click online training, unrestricted web/SQL tool, automatic cross-tenant learning, giant vector DB làm source of truth, hay multi-agent chỉ vì xu hướng.

## 26. Kết luận

Giữ nguyên OS-G0 → OS-G6. Mở rộng OS-G7 thành **Valora Intelligence Platform & Assistant**. Áp dụng ngay **AI-readable-by-design** vào domain slices, nhưng không kích hoạt runtime AI trước khi authoritative operating loop và task-specific gates được đóng.
