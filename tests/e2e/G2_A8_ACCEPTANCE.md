# A8 local product acceptance

Issue #126 candidate evidence only; Gate Owner integration and certification remain outstanding. Baseline: `311efca14b0bc639920edc355bbe521127a3c7e0`, exact-main CI #600 / run `37332543829` SUCCESS. A7 / #122 / PR #123 was certified at `d7efb4bf6a880b5d397807ed32acd99f929828a3`, exact-main CI #597 / run `37318932525` SUCCESS.

## Local-first evidence

Implementation, documentation reconciliation, T0/T1/T2, both browser runners and final diff inspection precede the first push. Reviewer reports and exact-head repository CI belong to the subsequent frozen candidate and PR evidence.

- T0: typed adapters, full-set contracts, reasons, denied/conflict/uncertain recovery, description save/preview/Human Commit, action mapping and selection acknowledgment tests.
- T1: affected Workbench, Asset Review, Case Overview and layout regressions; included in the full frontend run.
- T2: frontend lint/type compile, production build and bundle guard PASS; 410 frontend tests PASS; npm audit reports zero vulnerabilities. Backend Ruff PASS; 66 PostgreSQL A7/read/schema tests PASS. Existing Pydantic/SQLAlchemy deprecation warnings remain. Fluent primitives add a build chunk warning: about 649 kB minified / 183 kB gzip; no dependency versions already in the baseline changed.
- T3: real Chromium/Chrome, Vite frontend, FastAPI, PostgreSQL 16 and synthetic object storage; no intercepted/mocked API responses and no official lifecycle/proof SQL in the browser runners. The existing A5 bootstrap invokes real guarded-entry/Intake/Apply helpers, replaces its private test role with migrated standard roles, and supplies three sealed synthetic members. No customer data or live service credentials are used.

The recorded runtime reused `valora-g11k-backend:latest` with current backend sources mounted into `/app`; pytest/ruff/xlwt were installed in that isolated container. The Compose file also supports building the current backend locally. Existing migrations were applied to the fresh acceptance database; no migration or grant was changed.

## Browser matrix

| Scenario | Evidence |
| --- | --- |
| Asset Review prerequisite → Workbench preparation | `03-review-complete-preparation-action`; Case Overview's existing Next Action opens Workbench without a mutation |
| Missing descriptions | `02-description-required`; official descriptions empty, confirmation unavailable; existing validation warning requires description repair before review |
| Draft distinct from official; explicit Human Commit | Three `03-description-*-draft` checkpoints; API reads prove official values unchanged before Human Commit |
| Exact whole-set confirmation despite one-row filter | Confirm request includes three sealed members; dialog scope is three, filter shows one |
| Optional price absent | All three official prices remain null when authoritative Workbench becomes COMPLETE |
| Official description change → STALE | `06-stale-after-change`; public Case State preserves existing provider diagnostics |
| Renew review proofs and reconfirm with required reason | `07-reconfirmed`; reasonless button disabled before explicit entry |
| Explicit reasoned withdrawal | `08-withdrawn`; coherent INCOMPLETE retains prior confirmation identity |
| Concurrent official quantity change → 409 | `09-conflict-refresh-no-replay`; exactly one denied POST, authoritative refresh, renewed review and fresh explicit confirmation |
| Downstream hold after COMPLETE | `10-final-downstream-hold`; current stage ASSET_WORKBENCH, `NO_AUTHORIZED_DOWNSTREAM_ACTION`, no PRICE_EVIDENCE CTA |
| Authentication, contract, RBAC, tenant and closed session | `browser-negatives.json`: 401 / 400 / 403 / 404 / 404 |
| Denied mutation access preserves read-only COMPLETE | Viewer browser screenshot and public Case State remain COMPLETE; mutation controls absent |
| Keyboard and laptop | Cancel and Escape return focus; reasonless destructive action disabled; grid remains usable at 1024×768 |

Raw protected reason text is excluded from JSON evidence. Screenshots contain synthetic descriptions only. Evidence files are under `evidence/g2_a8/`; timestamps/fixture IDs describe this local run, not a certification claim.

## Architecture and authority

Existing Valora tokens and StatusBadge plus Fluent light Button/Field/Textarea/Dialog primitives supply presentation. Typed adapters and feature components contain new orchestration; WorkbenchLayout only composes the region and existing hooks. A scrollable stage area preserves the grid. Selection uses the existing lower-case target contract and resumes the session after a successful selection save so heartbeat uses a fresh server version.

Case State is the sole stage/result/Next Action source. Command eligibility and the entire sealed version set come from a typed, tenant/session/edit-scoped REPEATABLE READ snapshot. The read exposes no descriptions, protected reasons or internal proof vectors and writes no facts. The second minimal backend correction permits existing Workbench diagnostics in the public response schema, including inherited upstream diagnostics; it introduces no stage/result/action enum or predicate. GPT-6 Astra / High reviewed both authority gaps before their respective corrections.

Description edits use only the existing draft save and explicit Human Commit endpoints. Standard operators lack the separate `workbench:read` permission for inline-draft values; the editor reads authorized draft metadata, distinguishes an existing draft from official text, and requires a fresh explicit save/preview before applying after reload. No new grant is added.

Dialogs bind to the snapshot presented to the user. Changed eligibility or refresh invalidates confirmation. Success refreshes Case State rather than setting COMPLETE locally. Unknown whole-set outcomes retain only actor/project-scoped command UUID/contract metadata, reconcile scoped receipts and block further commands until resolved; reasons and CAS tokens are not stored. A 409 refreshes and requires new explicit confirmation. Non-DRAFT completion remains visible while the preparation read disables writes.

PRICE_EVIDENCE+ changed: NO. No membership, permission, migration, native, workflow, final-appraisal or later-stage runtime change. Full OS-G2 remains PARTIAL. A8 is an uncertified implementation candidate.

## Reproduce locally

Use an isolated fresh database and free localhost ports 8000, 5173 and 55438. From the repository root:

1. Build/start `docker compose -p valora-a8 -f tests/e2e/compose.g2_a8.yml up -d --build`. Alternatively set `A8_BACKEND_IMAGE` to an already installed compatible backend image; current sources are mounted.
2. Install the backend's existing development dependencies inside the acceptance container (`pip install -e '.[dev]'`), run `alembic upgrade head`, and provision its synthetic S3 bucket using the existing boto3 client.
3. Run `/acceptance/bootstrap_g2_a5.py` in the backend container with `PYTHONPATH=/app`, a test-only `A5_SYNTHETIC_PASSWORD`, and an unused `SYNTHETIC_ORGANIZATION_SLUG`. Record its project UUID. Run it again with a different slug for the foreign-tenant negative.
4. Start `npm run dev -- --host 127.0.0.1 --port 5173` from `frontend`; the existing Vite proxy targets port 8000.
5. Install Playwright in the runner environment and use Chrome, or set `A8_BROWSER_CHANNEL` to an available supported Chromium channel. Set `A8_PROJECT_ID`, `A8_ORGANIZATION_SLUG`, `A8_SYNTHETIC_PASSWORD`, and `A8_EVIDENCE_DIR`. Run `python tests/e2e/run_g2_a8_live.py` (Windows: `python -X utf8`).
6. Set `A8_FOREIGN_PROJECT_ID` to the second synthetic tenant's project, then run `run_g2_a8_negative.py`. It closes the owned synthetic session after proving completion.

Use a new synthetic project for each full positive run; the confirmation history is immutable. PostgreSQL integration tests use `TEST_DATABASE_URL=postgresql+psycopg://...` and isolate their schemas. The browser scenario deliberately changes descriptions and quantity only through existing real APIs. No external provider account is required.
