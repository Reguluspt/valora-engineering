# VALORA-ONEDRIVE-EXCHANGE-001 — OneDrive Personal Exchange v1

**Status:** COMPLETE — G8 OFFLINE ACCEPTED
**Opened:** 2026-09-20, Asia/Saigon
**Authority:** ADR 0044 + `VALORA_ONEDRIVE_EXCHANGE_V1_CONTRACT.md`; DOCX Working-copy promotion semantics are subsequently amended by ADR 0045

## Goal

Implement and prove the offline Exchange foundation for App Folder Inbox, Working and Exports while
OneDrive remains non-authoritative and DOCX/XLSX mutations stay behind their existing explicit
authority gates.

## Sequence and verification

1. Freeze ADR/contract/schema. Verify against ADR 0029/0040–0043 and storage contract.
2. Add capability ledger and Exchange migration. Verify upgrade/down/up and PostgreSQL isolation.
3. Add bounded Graph port/fake/write reconciliation. Verify no target escape or blind retry.
4. Add bounded blob read and DOCX initial/next-revision orchestration. Verify E1/E3–E7/E9/E11/E27.
5. Route XLSX through existing intake. Verify E2/E8/E10/E12/E28/E29.
6. Add minimal capability-aware M365 UI. Verify read-only and write-ready states/copy.
7. Run E1–E30, T1–T14, L1–L17, PostgreSQL and full affected suites/static checks.
8. Freeze one exact manifest and obtain independent DeepSeek and Gemini reviews.
9. Resolve valid findings, refreeze/re-review if bytes change, commit/push, then require exact-head CI.

## Prohibitions

No live Microsoft/AWS call, credentials, customer data, deploy, release, PR Ready or merge. No broad
`Files.ReadWrite` fallback and no change that makes OneDrive or spreadsheet save authoritative.

## Gate record

| Gate | State |
|---|---|
| G8-A contract/schema freeze | ACCEPTED — ADR 0044 and implementation contract |
| G8-B through G8-G implementation/tests | COMPLETE — offline suites, PostgreSQL proofs and static checks green |
| G8-H exact snapshot | COMPLETE — corrected snapshot refrozen and findings resolved |
| G8-I/J independent reviews | ACCEPTED — both independent reviewers accepted the corrected exact snapshot |
| G8-K commit/push | COMPLETE — G8 code milestone ends at `f896f15b0b18e8eb3a32619bee2418f3a4b92da4` |
| G8-L exact-head CI | PASS — GitHub CI #302; backend 1659 passed, frontend 140 passed, worker and whitespace jobs green |

## Post-G8 semantic reconciliation — 2026-09-21

G8 acceptance proves the offline Exchange/storage mechanism. It does **not** preserve the historical
product meaning that a changed Working DOCX may immediately become Revision N+1 merely because the
explicit re-import command was invoked.

ADR 0045 and the Working Change Observation design addendum now govern future DOCX Working behavior:

```text
provider change / return
→ automatic observation + exact revalidation
→ DocumentChangeCandidate + Old/V/W analysis
→ recommendation / review / conflict decision
→ explicit human confirmation
→ approved revision command
→ reuse G8 NEXT_REVISION + immutable storage + CurrentHead CAS
```

No G9/live Microsoft activity is opened by this closeout. G9 requires separate Product Owner
authorization and remains a bounded provider-conformance decision.
