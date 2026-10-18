# Issue 208 disposable acceptance harness

This is developer evidence for [the accepted Phase 2 contract](https://github.com/Reguluspt/valora-engineering/issues/208#issuecomment-6251855643), not PO #203 UAT. All identities, Projects and bytes are generated synthetic #208 data. Do not mount/connect #199 or use original #205 files.

`compose.yml` uses the already cached `postgres:16` and `valora-g11k-backend:latest` images with `pull_policy: never`. Source mounts are read-only. PostgreSQL and blob volumes belong only to `valora-issue208-20261018`; its sole Docker network is internal and neither service publishes a host port. The local immutable root belongs to its own blob volume. No shared/host configuration, new image download or system package installation is needed.

The browser transport is task-only: `api_bridge.py` binds loopback 58208 and forwards HTTP to the actual backend's loopback through a persistent Docker exec pipe. It neither retries a failed mutation nor opens an outbound Docker route. `serve.mjs` serves the current frontend on loopback 51208 and proxies to that transport. Restart the bridge after restarting/recreating the task backend. No bridge code is included in the production app.

## Setup and execution

From the dedicated worktree root, use the existing Docker CLI and cached project Python/Node/Playwright dependencies. The original baseline preflight recorded PostgreSQL 16.15, a single Alembic head `e8f9a0b1c2d3`, real auth/Case State and create-only/full-byte local storage. The new sole head is `f9a0b1c2d3e4`.

```text
docker compose -f tests/e2e/issue208/compose.yml up -d --pull never
docker compose -f tests/e2e/issue208/compose.yml exec -T backend python -m alembic upgrade head
docker compose -f tests/e2e/issue208/compose.yml exec -T backend python /acceptance/acceptance.py
docker compose -f tests/e2e/issue208/compose.yml exec -T backend python /acceptance/faults.py
docker compose -f tests/e2e/issue208/compose.yml exec -T backend python /acceptance/input_safety.py
docker compose -f tests/e2e/issue208/compose.yml exec -T backend python /acceptance/migration.py
```

For a repeat preflight against the new head, pass `-e ISSUE208_EXPECTED_MIGRATION_HEAD=f9a0b1c2d3e4` to `compose exec` before `backend python /acceptance/preflight.py`. Its default expectation remains the original baseline head.

In separate task processes, run the existing Python interpreter with `tests/e2e/issue208/api_bridge.py` and Node with `tests/e2e/issue208/serve.mjs`. Set `ISSUE208_EVIDENCE_DIR` to a task-private output directory and `ISSUE208_SYNTHETIC_PASSWORD` to the synthetic value configured in this task's Compose environment. Run `tests/e2e/issue208/browser.py` with an existing compatible Playwright and Chrome. `ISSUE208_BROWSER` may select an existing browser executable; the default is the installed Chrome on Windows. Do not download browsers as a fallback. The runner creates fresh normal/lost-response/viewer/stale fixtures, uses real login and server responses, and captures screenshots plus a metadata-only result JSON.

Existing regression tests use the task's PostgreSQL connection only. A test requiring PostgreSQL must not silently skip. The local storage DAC test must also run as a non-root Linux user; its root-mode skip is incomplete until the same test passes under a non-root UID. Task-private test databases/schemas are created/dropped only within this PostgreSQL service. `migration.py` checks an independently created `issue208_migration_` database through upgrade/downgrade/upgrade, unchanged role grants and no historical backfill.

## Evidence map

| Contract cases | Evidence runners |
| --- | --- |
| TXT-01,02,04,05,10,17,24,28,32 | `acceptance.py`, `faults.py`, `browser.py` |
| TXT-03 | Parser/calendar unit tests, real PostgreSQL calendar fixture and lock-wait/time-zone test in `faults.py` |
| TXT-07 | Bound-object cleanup denial in `faults.py`; no finalized purge/expiry capability |
| TXT-11..16,18..23,26,27 | Real PostgreSQL/local-store auth, CAS, lock, rollback, recovery and source-fault tests in `faults.py` and `input_safety.py` |
| TXT-25,28 | Existing document storage, local adapter and A13/A14 regressions, including real PostgreSQL |
| TXT-29,30 | `input_safety.py` and focused parser tests |
| TXT-31 | Browser preview, keyboard/focus, cancellation, one POST, denied/conflict/uncertain states and GET reconciliation; controller tests |
| TXT-33 | `migration.py`, schema constraints and immutable-row tests in `faults.py` |
| TXT-34 | Task-only command/resource evidence and internal network ownership |
| TXT-06,08,09 | **DEFERRED** future separately authorized capabilities/operator session; do not run or claim PASS |

The cached image's application/runtime dependency inventory is audited separately from its unused pre-existing package installer. The selected cached image contains PyJWT 2.15.1; its runtime library inventory and frontend dependencies are scanned without installing anything. Preserve the initial complete cached-image audit and its installer findings as historical tooling evidence; never describe that whole-image scan as clean. The cached dependency image is a local test base, not a proposed production image or deployment artifact.

On interruption, preserve the task worktree and raw private evidence; do not reset/clean another worktree or push unfinished code. No source change, Draft PR, independent review, CI result or readiness status is implied by this README. Freeze and inspect one completed candidate under the repository's separate delivery gates.
