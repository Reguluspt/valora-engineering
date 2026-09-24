# AI-PR-010 — Shadow Evaluation Harness

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME<br>
**Program:** VALORA AI Master Plan v1.0<br>
**Roadmap placement:** OS-G7.8<br>
**Depends on:** AI-PR-007/009 accepted; evaluation fixtures approved<br>
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable<br>
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Đo AI so với deterministic baseline và independent human outcome trong shadow mode.

## 2. Scope
Versioned corpus, no-write shadow runner, leakage controls, model/prompt/retriever comparison, regression reporting.

## 3. Required deliverables
- dataset manifest/version;
- split/leakage rules;
- shadow runner;
- correction/false-high-confidence/unsupported/citation/retrieval/latency/cost/review-time metrics;
- reproducible report.

## 4. Acceptance gate
No write side effects; exact release reproducibility; leakage tests; fallbacks evaluated separately; committed human outcomes distinguished from AI agreement.

## 5. Forbidden scope
Clicks as labels by default; per-click online training; confidence-based promotion; hidden eval tuning.
