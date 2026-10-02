# OS-G2 A5 Asset Review product closure — acceptance blocked

## Snapshot and authorization

Task: Issue #81. Implementation baseline: `416157e6330f861127455a66fd5df9c0972bc02a`, exact-main [CI #545 SUCCESS](https://github.com/Reguluspt/valora-engineering/actions/runs/37004731799). Branch: `codex/os-g2-a5-asset-review-product-closure`.

Status: **BLOCKED — no frozen candidate HEAD or certification claim.** The frontend changes are uncommitted work. No independent candidate reviews, candidate CI, Draft PR, Ready transition or merge have been performed.

## Setup and actual evidence

- Fresh acceptance database `issue81_acceptance`, real PostgreSQL at `127.0.0.1:55475`; accepted migrations applied from base to sole head `a4b5c6d7e8f9`.
- Real RustFS/S3 at `127.0.0.1:55476`, including source workbook and generated Result bytes. FastAPI at `127.0.0.1:8001`, local transport forwarding at `127.0.0.1:8000`, Vite at `localhost:5173`.
- `tests/e2e/bootstrap_g2_a5.py` uses existing real lineage, Analysis, Result, Intake, staging validation and guarded Apply commands. It creates synthetic identities and associates migrated standard owner/viewer roles; it does not alter role permissions or write official status/proof facts directly.
- Synthetic Project `A5-SYNTH-001`, UUID `4fa13711-cb1b-43bf-8579-5012bb8b729b`, three sealed official lines. Organization slug `a5-synthetic`; operator `operator@a5.invalid`; no client data. Password is generated locally and is excluded from repository/evidence.
- Browser authenticated the standard owner through the real login API. Case Overview showed all four Pre-case stages COMPLETE, ASSET_REVIEW current and INCOMPLETE, eleven later stages NOT_AVAILABLE. Its session-required bridge opened the existing Workbench.
- Opening Workbench attempted the existing session POST and received **403**. No validation or review command was submitted. PostgreSQL readback: zero validation generations, decisions, reversals, command receipts and A4 command audits.

## Exact authority conflict

At the baseline, `backend/app/api/workbench.py` declares the session creation dependency `require_permission("workbench:open")`. The accepted migrated owner/appraiser roles contain `workbench:edit` but do not contain `workbench:open`. A read-only query of the freshly migrated roles found no role containing `workbench:open`.

The A4 provider correctly returns `UNAVAILABLE`, `ASSET_REVIEW`, null semantic target and `context.reason_code=session_required` while preserving stage truth. Session creation cannot satisfy this prerequisite for the migrated standard operator. Existing command access remains backend-authoritative; the frontend has not bypassed it.

Issue #81 prohibits new RBAC/grants and backend semantics, and requires stopping if backend semantics need to change. Therefore no grant, endpoint permission change, fixture shortcut with elevated custom permissions, or preinserted Workbench session was used to manufacture acceptance. Gate Owner must resolve the session-establishment permission boundary under separate accepted authority before the required product journey can be certified.

## Completed development checks

- API/controller/routing/status/Workbench focused checks: **27 passed**.
- Grid/controller/pagination focused checks: **34 passed**.
- Frontend lint: PASS; frontend build and production-bundle guard: PASS.
- Full frontend unit suite run once: **324 passed, 46 files**.
- Full PostgreSQL browser journey, negative cases, unknown-response certification, dialog focus certification and full-set COMPLETE: **NOT COMPLETED**.

## Repository-local visual references and captures

The S10 composition uses `docs/design/visual-reference/v2.3/baselines/s10-orchestration-hub-iteration-2-approved.png` (Part 2B PDF p. 3, Iteration 2). Existing Workbench uses `s12-workbench-approved.png` (Part 1 PDF p. 14); contextual drawer uses `s13-asset-context-drawer-approved.png` (Part 1 PDF p. 15). Source PDFs and authority precedence are recorded in `docs/design/visual-reference/v2.3/README.md`.

The first image is a browser capture of the incomplete acceptance attempt, not visual acceptance or completed product evidence:

1. [Pending Case Overview](g2-a5-screenshots/01-case-overview-pending.jpg).

The old `02-session-rbac-blocked.jpg` capture is entirely blank (one uniform color). It is **invalid evidence**, is excluded from the candidate, and is not accepted as browser proof of the RBAC blocker. Fresh post-A5R2 real-stack browser captures must supersede it. Investigate the capture infrastructure only if the blank-image failure reproduces.

No final COMPLETE capture exists. ASSET_WORKBENCH+ remains unauthorized.

READY FOR GATE REVIEW: NO
