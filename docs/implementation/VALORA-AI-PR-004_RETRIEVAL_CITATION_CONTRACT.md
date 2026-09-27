# AI-PR-004 — Retrieval & Citation Foundation

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME<br>
**Program:** VALORA AI Master Plan v1.0<br>
**Roadmap placement:** OS-G7.3<br>
**Depends on:** AI-PR-003 accepted; lineage/source locators available<br>
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable<br>
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Chuẩn hóa retrieval và claim-to-source citation.

## 2. Scope
Structured lookup first; SQL/FTS/domain similarity; optional embeddings only as derived projection; define SourceRef/CitationRef and RetrievalIndexRelease.

## 3. Required deliverables
- retriever interface/versioning;
- source/citation schema;
- claim-to-source response contract;
- index release metadata;
- rebuild rules;
- evaluation fixtures.

## 4. Acceptance gate
Derived index rebuild không mutate authority; citations resolve tenant-safely; unsupported claims detectable; vector DB không bắt buộc.

## 5. Forbidden scope
Vector DB source-of-truth; loss of lineage; cross-tenant retrieval; unregistered Internet retrieval.
