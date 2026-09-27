# AI-PR-006 — Typed Read Tool Registry

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME<br>
**Program:** VALORA AI Master Plan v1.0<br>
**Roadmap placement:** OS-G7.5<br>
**Depends on:** AI-PR-003/004 accepted; target read models complete<br>
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable<br>
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Cho Assistant đọc VALORA qua typed tenant-safe tools, không direct SQL.

## 2. Scope
Read tools cho case, asset, evidence, quotes, knowledge, dossier, pricing, document snapshots; mỗi tool có schema/permission/tenant/version/budget/audit.

## 3. Required deliverables
- tool registry;
- read-only adapters;
- per-tool permissions/budgets;
- result bounds/pagination;
- tool-call provenance.

## 4. Acceptance gate
Không tool nào mutate; cross-tenant fail closed; bounded schema-valid output; safe typed failures; không generic SQL/filesystem/network tool.

## 5. Forbidden scope
execute_sql; arbitrary repository access; mutation tools; final-price/publish/signature tools; open web browser.
