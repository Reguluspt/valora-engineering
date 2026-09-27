# AI-PR-011 — Model / Prompt / Retriever Release Registry

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME<br>
**Program:** VALORA AI Master Plan v1.0<br>
**Roadmap placement:** OS-G7.8<br>
**Depends on:** AI-PR-010 accepted<br>
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable<br>
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Đóng gói capability AI thành evaluated versioned release có rollback/disable độc lập.

## 2. Scope
Registry linking task/schema/prompt/model/provider/retriever/index/policy envelope/evaluation/deployment state/rollback/kill switch.

## 3. Required deliverables
- release registry contract;
- shadow/review-only/active/blocked states;
- metric references;
- rollback/kill-switch commands/audit;
- drift downgrade rules.

## 4. Acceptance gate
Unreleased combination không active; rollback deterministic; kill switch tested; drift degrades; release change audited/human-controlled.

## 5. Forbidden scope
Global AI_ON authority; silent model swap; confirmation-count promotion; R3/R4 promotion.
