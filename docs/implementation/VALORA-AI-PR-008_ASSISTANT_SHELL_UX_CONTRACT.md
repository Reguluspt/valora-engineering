# AI-PR-008 — Valora Assistant Shell & UX

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME  
**Program:** VALORA AI Master Plan v1.0  
**Roadmap placement:** OS-G7.7  
**Depends on:** AI-PR-007 accepted; Fluent 2 surfaces stable  
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable  
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Tạo Trợ lý Valora gắn project/case/screen context, không biến chat thành source of truth.

## 2. Scope
Assistant session/read surface, Vietnamese-first Fluent 2, context binding, citation rendering, task states, retry, safe suggested actions, bounded UX history.

## 3. Required deliverables
- AssistantSession contract;
- Fluent 2 panel/drawer;
- citation UX;
- loading/error/blocked/stale/provider-unavailable states;
- accessibility;
- no provider branding.

## 4. Acceptance gate
Assistant failure leaves product usable; chat không mutate business/learning; screen context server-authorized; citations inspectable; browser/visual acceptance.

## 5. Forbidden scope
Standalone workflow axis; hidden auto-apply; chat-only business state; ordinary-user provider/model control.
