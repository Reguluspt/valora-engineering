# OS-G2 A5 Asset Review product closure — real-stack evidence

## Authority and reconciliation

Issue #81, branch `codex/os-g2-a5-asset-review-product-closure`. Preserved A5 work was checkpointed at `9cde874`; `origin/main` was fetched and verified as `7c52a41a84b21b63182429d5c5740e76783ea4e6`. Main was merged at `5a847be87c3793d1f7f8a50216590aa7189863b8`. Exact-main CI #552, run 37030952607, succeeded. Issue #84 was closed, PR #85 merged at that SHA, and Alembic head is `b5c6d7e8f9a0`. The certified owner/appraiser `workbench:open` grant removed the earlier session blocker. ASSET_WORKBENCH and later runtime remain unauthorized.

## Stack and synthetic data

- PostgreSQL acceptance database `issue81_acceptance`, migrated to `b5c6d7e8f9a0`; real RustFS/S3 source workbook and Result bytes; FastAPI, local response-drop proxy and Vite at `http://localhost:5173`.
- `tests/e2e/bootstrap_g2_a5.py` used real lineage, Analysis, Result, Intake, staging validation and guarded Apply commands. Synthetic standard owner and viewer roles came from accepted migrations. No direct SQL writes to official status/proof facts, custom grants, session insertion or real customer data.
- Synthetic Project `A5-SYNTH-001`, UUID `4fa13711-cb1b-43bf-8579-5012bb8b729b`, with three sealed official lines. Owner `operator@a5.invalid`, viewer `viewer@a5.invalid`; password remains outside the repository.
- Browser owner authentication and `POST /api/v1/workbench/sessions` established the real owned session. Case State was refetched before mutation actions appeared.

## Browser journey and recovery matrix

Case Overview initially showed all four Pre-case stages COMPLETE, ASSET_REVIEW current/INCOMPLETE and eleven later stages NOT_AVAILABLE. Its CTA opened the existing Workbench. Each validation and review POST followed a visible human confirmation. Valid validation created a current proof; Chấp nhận then created the separate human decision. Authoritative next action advanced to the first unfinished line. All three lines were accepted.

| Scenario | Observed real-stack result |
| --- | --- |
| Warning | Blank official description produced `description_blank` warning. No Accept CTA; stage remained INCOMPLETE. |
| Invalid | Official quantity zero produced `quantity_invalid`. UI required correction and offered no Accept CTA. |
| Flagged/rejected | Both held the stage BLOCKED; positive reversal required fresh validation and a reasoned human confirmation. |
| Stale version | An official quantity edit between dialog opening and confirmation produced 409. UI displayed a localized conflict, refetched grid and Case State, and did not resubmit. |
| Permission | Standard viewer received Workbench session permission denial; with a pending line, no working review mutation CTA appeared. |
| Unknown POST result | A one-shot proxy dropped a successful validation response. The same command UUID `35087264-f1b0-49e4-918b-69125410325b` was reconciled by one scoped receipt GET; the transport log has one POST. No duplicate proof or audit was created. |
| Official value change | Editing a previously accepted line invalidated its current proof and reverted ASSET_REVIEW to INCOMPLETE. Browser followed `asset_review_line_validate_required`, then required fresh validation and a reasoned human decision to restore completion. |
| Downstream boundary | Final Case State retained `current_stage=ASSET_REVIEW`, returned `next_action.kind=NO_AUTHORIZED_DOWNSTREAM_ACTION`, and left every later stage NOT_AVAILABLE. No fake Continue CTA appeared. |

Final PostgreSQL readback: ASSET_REVIEW COMPLETE, all three official lines `accepted` with current `valid` validation, 7 validation generations, 6 human decisions, 3 reversals, 13 scoped receipts, 7 validation audits and 6 decision audits. After a browser reload, Case Overview reconstructed 5/16 completed stages and showed “Chưa có hành động tiếp theo được phép”; Workbench reconstructed “Hoàn tất rà soát tài sản”.

## Screenshots and capture validity

The old `g2-a5-screenshots/02-session-rbac-blocked.jpg` is entirely blank (one uniform color), **INVALID EVIDENCE**, excluded from the candidate and not accepted as browser proof. It remains untouched locally. Fresh post-A5R2 real-stack browser evidence supersedes it.

The blank-image issue reproduced for a new Workbench `fullPage: true` capture. Investigation isolated it to that capture mode: a viewport capture of the same rendered page was nonblank. All accepted captures below use `fullPage: false` and were checked for multiple pixel colors. The new blank diagnostic capture was discarded; the old `02` remains untouched.

- [Pending Case Overview after A5R2](g2-a5-screenshots/03-case-overview-pending-a5r2.jpg)
- [Workbench validation required](g2-a5-screenshots/04-workbench-validate-required.jpg)
- [Rejected hold and reversal](g2-a5-screenshots/06-rejected-reversal-required.jpg)
- [Case Overview complete](g2-a5-screenshots/07-case-overview-complete.jpg)
- [Workbench complete](g2-a5-screenshots/08-workbench-complete.jpg)
- [Viewer permission blocked](g2-a5-screenshots/09-viewer-permission-blocked.jpg)
- [Value change requires revalidation](g2-a5-screenshots/10-value-change-revalidate.jpg)

The earlier [pending Case Overview](g2-a5-screenshots/01-case-overview-pending.jpg) is historical pre-A5R2 context only, not final browser acceptance.

## Candidate checks

Post-reconciliation focused frontend tests: 26/26 passed. The full frontend suite ran once near the coherent candidate: 324/324 passed across 46 files. Frontend lint, build and production-bundle guard passed. Independent reviews, Draft PR and exact-head CI are separate candidate gates; this evidence does not authorize Ready, merge or later-stage runtime.
