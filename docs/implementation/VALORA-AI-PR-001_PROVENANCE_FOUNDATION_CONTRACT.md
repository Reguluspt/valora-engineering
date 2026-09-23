# AI-PR-001 — AI Provenance Models & Persistence

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME  
**Program:** VALORA AI Master Plan v1.0  
**Roadmap placement:** OS-G7.1  
**Depends on:** OS-G6 operating-loop gate + explicit assignment; AI-PR-000 accepted  
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable  
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Tạo provider-independent provenance cho bounded AI task.

## 2. Scope
Persistence cho `AITaskRun`, append-only `AITaskAttempt`, `AIContextManifest`, `DecisionEpisode`, `RetrievalIndexRelease`; reuse `LearningFeedbackEvent` khi compatible; link existing TaskJob.

## 3. Required deliverables
- migrations/models/schemas/services;
- tenant-scoped keys;
- append-only attempts/episodes;
- TaskJob linkage;
- task/schema/prompt/retriever/policy versions;
- bounded audit payload rules.

## 4. Acceptance gate
- PostgreSQL migration/single-head tests;
- cross-tenant fail closed;
- retry/fallback không overwrite attempt;
- không copy raw sensitive content;
- domain decisions vẫn authority;
- không cần provider thật.

## 5. Forbidden scope
External provider execution; new queue; direct AI domain mutation; invented legacy provenance.
