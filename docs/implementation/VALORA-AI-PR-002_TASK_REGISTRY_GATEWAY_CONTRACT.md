# AI-PR-002 — AI Task Registry, Model Policy & Deterministic Gateway

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME<br>
**Program:** VALORA AI Master Plan v1.0<br>
**Roadmap placement:** OS-G7.2<br>
**Depends on:** AI-PR-001 accepted<br>
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable<br>
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Tạo một đường gọi AI typed/versioned nhưng chỉ deterministic/mock ở slice đầu.

## 2. Scope
`AITaskRegistry`, input/output schemas, prompt metadata, `ModelPolicy`, `ProviderGateway`, deterministic/mock adapter, redaction/data-policy hook, fallback contract.

## 3. Required deliverables
- registry APIs/internal contracts;
- provider-neutral gateway;
- mock/deterministic adapter;
- schema validation;
- allowed provider/model/fallback metadata.

## 4. Acceptance gate
Unregistered task/model/fallback bị từ chối; malformed output fail; manual path đầy đủ; provider code không có DB mutation handle; context policy chạy trước execution.

## 5. Forbidden scope
Real provider calls; credentials; generic unrestricted chat endpoint; runtime tool calling; R2+.
