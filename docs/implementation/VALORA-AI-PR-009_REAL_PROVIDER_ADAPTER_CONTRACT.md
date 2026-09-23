# AI-PR-009 — First Real Provider/Model Adapter

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME  
**Program:** VALORA AI Master Plan v1.0  
**Roadmap placement:** OS-G7.2 / activation gate  
**Depends on:** AI-PR-001…008 accepted + explicit provider/data-policy authorization  
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable  
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Kết nối một provider/model thật qua ProviderGateway.

## 2. Scope
One approved adapter, secret/config boundary, timeout/rate/cost/error mapping, model release pinning, allowed fallback and data policy.

## 3. Required deliverables
- backend-only adapter;
- secret injection contract;
- exact model provenance;
- cost/latency telemetry;
- allowed task list;
- evaluated/manual fallback.

## 4. Acceptance gate
No secret exposure; only registered tasks; redaction policy applied; unknown outcome recoverable; outage preserves manual path.

## 5. Forbidden scope
Multiple providers without need; silent alias drift; provider DB access; unrestricted source uploads; autonomous mutation.
