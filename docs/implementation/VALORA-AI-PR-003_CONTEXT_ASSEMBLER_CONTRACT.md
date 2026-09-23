# AI-PR-003 — Context Assembler & AIContextManifest

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME  
**Program:** VALORA AI Master Plan v1.0  
**Roadmap placement:** OS-G7.3  
**Depends on:** AI-PR-001/002 accepted; domain read models available  
**Authority:** Unified Roadmap v2.3 + VALORA AI Master Plan v1.0 + ADR 0033/0034 where applicable  
**Important:** File này là implementation contract tương lai. Sự tồn tại của file không cấp quyền coding/runtime/provider/autonomy.

## 1. Objective
Tập hợp bounded authoritative context và phát hành reproducible `AIContextManifest`.

## 2. Scope
Task-specific context policies cho case/asset/evidence/knowledge/dossier; derive tenant/actor server-side; preserve versions/hashes; redact/classify before model.

## 3. Required deliverables
- Context policy interface;
- bounded context DTOs;
- manifest service;
- source refs/version/hash;
- redaction/classification;
- stale-generation hooks.

## 4. Acceptance gate
Deterministic manifest identity where required; cross-tenant impossible; bounded summaries instead of source dumps; stale detectable; chat history không tự thành authority.

## 5. Forbidden scope
Full DB dump; unbounded whole-document context; client-asserted tenant/actor; provider activation.
