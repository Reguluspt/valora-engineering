# VALORA-ONEDRIVE-EXCHANGE-001 — OneDrive Personal Exchange v1

**Status:** G8-H CORRECTED SNAPSHOT FROZEN FOR INDEPENDENT RE-REVIEW
**Opened:** 2026-09-20, Asia/Saigon
**Authority:** ADR 0044 and `VALORA_ONEDRIVE_EXCHANGE_V1_CONTRACT.md`

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
| G8-H exact snapshot | CORRECTED SNAPSHOT FROZEN AFTER FULL RE-VERIFICATION |
| G8-I/J independent reviews | PRIOR: Gemini ACCEPT / DeepSeek REJECT; both must rerun on the corrected snapshot |
| G8-K commit/push | NOT STARTED |
| G8-L exact-head CI | NOT STARTED |
