# Valora Test and CI Baseline

| Field | Evidence |
|---|---|
| Task | PM-OPS-005-01 / Issue #167 (parent #166) |
| Recorded | 2026-10-09 11:42 UTC |
| Source baseline | `main` / `9ff396025272b483a9f2da653f11a35a132afea2` |
| CODEX blob | `de7e47d224a4f90bc190c182638d6a55c17540e5` |
| Exact-main gate | CI #656 / run [37911711466](https://github.com/Reguluspt/valora-engineering/actions/runs/37911711466), push on the source baseline, completed SUCCESS 5/5 |

**Requested route:** GPT-6 Luna / Medium. Actual native model metadata is unavailable; no execution-model claim is made.

## Findings

- The backend pytest step is the measured CI bottleneck: in the latest 12 successful runs (six push, six pull request), it averaged 36.75 minutes on push and 35.32 minutes on pull requests. It consumed about 97% of backend job elapsed time. Run #656 reports 2,331 passed in 2,137.46 seconds (35m37s); the enclosing step elapsed 36m15s.
- The backend local collection count of 2,310 on Windows reconciles numerically to the Linux CI execution count of 2,331: `backend/tests/test_document_blob_store_local.py` has exactly 21 test functions and module-skips on non-POSIX platforms. This is source-level reconciliation; a matching Linux node-ID collection comparison was not available, so full cross-platform node-ID parity is **NOT MEASURED**.
- The current workflow does not emit per-test or fixture setup/teardown durations. A top 20–30 slow-test ranking is **NOT MEASURED**. Test counts and large modules below are not timing rankings.
- Frontend and Windows Client test case counts were unavailable locally because the checkout environment has no frontend `node_modules` and no .NET SDK. No dependencies were installed to fill those gaps.
- The workflow runs all five jobs for both pull requests and pushes to `main`, with no path filters. A tooling-oriented PR therefore also runs the full backend suite; this is an observed cost candidate for a separately authorized CI policy audit, not a proposed change in this task.

## Baseline and method

All source inspection and collection used the isolated clean task checkout at the baseline above. CI run and job data came from GitHub Actions records read with `gh run list` and `gh run view`; step durations are `completedAt - startedAt`. Queue delay is earliest job start minus run creation. Active workflow elapsed is latest job completion minus earliest job start. Estimated runner-minutes sum completed job elapsed durations for one workflow attempt; concurrent job times are deliberately not added to workflow wall time. All timestamps are UTC. The 12-run sample consists of six recent successful `push` runs and six recent successful `pull_request` runs, each attempt 1. Canceled run [37739915789](https://github.com/Reguluspt/valora-engineering/actions/runs/37739915789) was observed in the broader recent list and excluded from successful-run averages.

### Test inventory

| Area | Static test files | Observed collection/discovery | Environment and limits |
|---|---:|---:|---|
| Backend pytest | 147 | 2,310 collected | Windows; Python 3.14.7, pytest 9.1.1; `backend/` collection. The source-level 21-test POSIX module is excluded by its module skip. |
| Backend Linux CI | Same source tree | 2,331 passed | Linux; workflow Python 3.12; exact-main #656 execution summary, not a collected-node list. |
| Worker pytest | 2 | 5 collected | Local collection with `PYTHONPATH` including sibling `backend` and current `worker`; without that path, import of `app` fails. No test bodies run. |
| Infrastructure server | 1 | 7 unittest cases discovered | `unittest.defaultTestLoader.discover`; discovery imports tests but does not execute test methods. |
| Scripts pytest | 2 | 64 collected | `python -m pytest --collect-only -q scripts/tests`; current workflow has no `scripts/tests` job. |
| Frontend Vitest | 59 | **NOT MEASURED** | Static file enumeration only; `frontend/node_modules`/local Vitest absent. No `npm install` or `npm ci` run locally. |
| Windows Client | 12 | **NOT MEASURED** | Static scan found 75 `[Fact]`/`[Theory]` declarations; theories may expand to multiple cases. `dotnet` reports no installed SDK. Current workflow has no Windows Client job. |

File counts are not test-case counts. Local test collection does not execute tests. The Linux CI pass count is an execution result, not a Linux collection result.

### Backend platform reconciliation

The source file [`test_document_blob_store_local.py`](https://github.com/Reguluspt/valora-engineering/blob/9ff396025272b483a9f2da653f11a35a132afea2/backend/tests/test_document_blob_store_local.py#L22-L27), Git blob `564133f25ace8508cecc4316bd776c2fc9fe2029`, checks for POSIX and `os.link`, then calls `pytest.skip(..., allow_module_level=True)` otherwise. AST enumeration at the same SHA found exactly 21 distinct `test_*` functions (lines 101–936), covering local filesystem document blob-store acceptance checks L1–L17. Thus `2,310 Windows-collected + 21 POSIX-only functions = 2,331`, matching the Linux CI run summary. The Windows module skip is intentional platform selection and is **not a pass**. No skip condition or test was changed.

### Skips and xfails

- CI #656 summary: `2,331 passed, 959 warnings`; the summary reports no skipped, xfailed, or xpassed cases.
- Local Windows marker selection with `pytest --collect-only -m skipif` selected 4 nodes; `-m skip` and `-m xfail` selected none. These are marker-bearing node counts, not execution outcomes.
- Other tests contain runtime `pytest.skip()` guards for unavailable PostgreSQL/S3/Node or platform prerequisites. Their conditions were not exercised by local collection. The all-passed #656 summary indicates those guards did not skip a test in that run.
- No test is proposed for deletion, skipping, weakening, or assertion changes.

## CI timing

### Recent successful runs

| Run | Event | Queue s | Active wall min | Estimated runner min | Backend job min | Backend pytest step min |
|---:|---|---:|---:|---:|---:|---:|
| [37911711466](https://github.com/Reguluspt/valora-engineering/actions/runs/37911711466) | push | 3 | 37.43 | 39.20 | 37.43 | 36.25 |
| [37884889977](https://github.com/Reguluspt/valora-engineering/actions/runs/37884889977) | push | 2 | 40.93 | 42.80 | 40.92 | 39.68 |
| [37864462434](https://github.com/Reguluspt/valora-engineering/actions/runs/37864462434) | push | 2 | 39.10 | 41.28 | 39.10 | 37.80 |
| [37794068112](https://github.com/Reguluspt/valora-engineering/actions/runs/37794068112) | push | 3 | 39.50 | 41.43 | 39.50 | 38.45 |
| [37772548650](https://github.com/Reguluspt/valora-engineering/actions/runs/37772548650) | push | 3 | 33.97 | 35.92 | 33.97 | 32.97 |
| [37745117988](https://github.com/Reguluspt/valora-engineering/actions/runs/37745117988) | push | 3 | 36.38 | 38.30 | 36.38 | 35.37 |
| [37902470077](https://github.com/Reguluspt/valora-engineering/actions/runs/37902470077) | pull_request | 3 | 38.37 | 40.23 | 38.37 | 37.28 |
| [37895502755](https://github.com/Reguluspt/valora-engineering/actions/runs/37895502755) | pull_request | 3 | 37.03 | 38.83 | 37.03 | 36.03 |
| [37892693567](https://github.com/Reguluspt/valora-engineering/actions/runs/37892693567) | pull_request | 2 | 38.82 | 40.78 | 38.82 | 37.83 |
| [37879124580](https://github.com/Reguluspt/valora-engineering/actions/runs/37879124580) | pull_request | 2 | 38.40 | 40.25 | 38.38 | 37.35 |
| [37878653226](https://github.com/Reguluspt/valora-engineering/actions/runs/37878653226) | pull_request | 2 | 26.68 | 28.58 | 26.67 | 25.50 |
| [37803730736](https://github.com/Reguluspt/valora-engineering/actions/runs/37803730736) | pull_request | 2 | 38.95 | 40.83 | 38.95 | 37.95 |

| Sample | Runs | Mean active wall | Mean estimated runner time | Mean backend job | Mean pytest step |
|---|---:|---:|---:|---:|---:|
| Push | 6 | 37.88 min | 39.82 runner-min | 37.88 min | 36.75 min |
| Pull request | 6 | 36.38 min | 38.25 runner-min | 36.37 min | 35.32 min |

The #656 backend job ran 09:30:29–10:07:55 UTC (37m26s). Its pytest step ran 09:31:29–10:07:44 UTC (36m15s); the pytest summary reports 2,137.46 seconds (35m37s). The workflow also started PostgreSQL and RustFS and ran dependency setup, static checks, migration/readiness checks, dependency auditing, and a security scan. These are step/job measurements; no test-case or fixture cost is available. All five #656 jobs completed successfully: backend, frontend, worker, server-foundation, and committed-whitespace.

Runner-minute totals are estimates from job elapsed durations, not billed minutes. GitHub billing records and applicable rate multipliers were not available, so actual charges and cost savings are **NOT MEASURABLE**. Queue delay was 2–3 seconds in this sample; this is not a general queue-performance claim.

### Workflow behavior and follow-up candidates

The workflow at [`.github/workflows/ci.yml`](https://github.com/Reguluspt/valora-engineering/blob/9ff396025272b483a9f2da653f11a35a132afea2/.github/workflows/ci.yml) starts five jobs on every pull request and on pushes to `main`, `s12-*`, `s13-*`, and `codex/win-0-windows-client-foundation`; it has no path filters. The jobs run in parallel. A tooling/report PR still receives the same backend, frontend, worker, server-foundation and whitespace jobs. For example, PR run #655 took 38.37 minutes active wall time, with a 38.37-minute backend job and 37.28-minute pytest step. The subsequent merged-main run #656 repeated all five required jobs. These runs demonstrate repeated full-gate execution across PR and main events; whether and how to alter required-check policy is outside #167.

Job and step records show these broad patterns in the sample:

- Backend `pytest -rs` dominates. PostgreSQL container initialization, RustFS startup, dependency installation, static checks, migration smoke/readiness checks and dependency/security scans occur in the same job; these steps are separate from pytest time.
- Frontend job averages about 0.9 minutes; `npm ci`, lint, build, Vitest, and `npm audit` all run on every workflow event.
- Worker job averages about 0.5–0.6 minutes and separately installs backend/worker dependencies, runs worker pytest, and runs `pip-audit`.
- Server-foundation averages about 0.3–0.4 minutes; committed-whitespace averages about 0.1 minutes.

Potential clusters for a later test-quality audit, not findings of redundancy:

1. Supplier Quotes is covered by domain, API, storage, product-projection, and PostgreSQL modules (`test_g2_supplier_quotes*.py`). Verify each layer's distinct invariant before proposing consolidation.
2. Case-state projection is split across aggregator, provider, endpoint, and PostgreSQL tests (`test_pr01_case_state_projection*.py`). Trace shared fixtures and unique state/tenant assertions before claiming duplication.
3. S13-PR-002 source-artifact and corrective tests recur across multiple acceptance modules; compare the authored evidence matrix, fixtures and asserted invariants before labeling overlap.
4. S12-PR-004 staging/apply tests span apply, proof-matrix, corrective-proof and acceptance-closure modules. Keep migration, CAS, audit, and replay protections explicit in any future review.

The highest-volume Windows-collected backend modules were `test_s13_pr_003_workbook_structure.py` (123 nodes), `test_pr01_preliminary_analysis_service.py` (109), `test_g2_line_decisions.py` (63), `test_s12_r_004_official_mutation.py` (55), and `test_g2_asset_workbench.py` (52). These counts identify volume only; they do not predict duration or redundancy.

## Backend fixtures and slow-test evidence

[`backend/tests/conftest.py`](https://github.com/Reguluspt/valora-engineering/blob/9ff396025272b483a9f2da653f11a35a132afea2/backend/tests/conftest.py#L19-L108) defines two autouse fixtures (default function scope):

- `_s13_pr_002_strong_helper_runtime_guard` clears helper evidence context for each test; marked nodes also set runtime identity, look up the static ledger, validate case evidence after the test, and clear context in `finally`.
- `setup_test_auth` installs a FastAPI dependency override before each test and removes it afterward.

Module-local fixtures are also common. [`backend/tests/test_db.py`](https://github.com/Reguluspt/valora-engineering/blob/9ff396025272b483a9f2da653f11a35a132afea2/backend/tests/test_db.py) creates and drops an in-memory SQLite schema inside a test. PostgreSQL concurrency/migration tests, S3/RustFS storage tests, and tests using temporary filesystem roots appear in separate modules. CI creates PostgreSQL and RustFS services and starts Redis for its dependency-readiness proof before the backend suite. Static source inspection identifies setup mechanisms only; it does not measure fixture setup/teardown or show that any particular fixture causes the long runtime.

**Slowest tests, setup/teardown timings, and per-module execution timings: NOT MEASURED.** CI invokes `pytest -rs` without `--durations`, and the retrieved logs contain aggregate results only. No individual test ranking is inferred from node counts, filenames, fixture names, or test purpose. A future specifically authorized profiler can record `--durations=30` and fixture timings in one isolated Linux/Python 3.12 environment with disposable PostgreSQL/RustFS/Redis; this task did not run another 35–40 minute suite.

## Reproduction and verification record

Commands run locally (test bodies were not executed):

```powershell
# From backend; Windows Python 3.14.7 / pytest 9.1.1
python -m pytest --collect-only -q

# From worker; supply sibling backend source for imports
$env:PYTHONPATH = "../backend;."
python -m pytest --collect-only -q

# From repository root
python -m pytest --collect-only -q scripts/tests

# Infrastructure unittest discovery without running tests
python -c 'import unittest; s=unittest.defaultTestLoader.discover("infra/server/tests"); print(s.countTestCases())'

# GitHub run/job/step records (repeat for each run ID in the timing table)
gh run view <RUN_ID> --repo Reguluspt/valora-engineering --json databaseId,event,createdAt,jobs
```

Frontend Vitest and Windows Client test discovery commands were not run because their required local runtimes/dependencies were unavailable. Existing workflow configuration supplies their execution commands (`npm run test`; Windows Client is not a job in this workflow). A read-only Python 3.12 Linux container was available, but the Python 3.12 backend images checked did not contain pytest; no package was installed, and no Linux collection or node-ID parity claim is made.

- **T0:** run durations were calculated from UTC timestamps; the CI attempt was joined to its exact run SHA; runner-minute sums include each successful job once; file counts, collected nodes, marker nodes, and executed passes are labeled separately. `2,310 + 21 = 2,331` was source-reconciled without equating execution counts to a node-ID inventory.
- **T1:** exact-main #656 job/step timestamps and pytest summary were checked against native GitHub records; 12 run records (six push, six PR) were cross-checked at job and backend-step level. Local pytest collection was reproduced from the pinned source. The POSIX module blob and all 21 test function declarations were checked locally.
- **T2:** source links pin the baseline SHA; the report contains aggregate timings, test identities and non-sensitive counters only. No credentials, customer payloads, raw logs, or private data are included. Whitespace and changed-path checks are recorded on the candidate before delivery.
- **T3:** product runtime, browser, and PostgreSQL proof are N/A for this documentation-only audit; no test suite or service-backed test was run locally.

## Disposition and limitations

This report documents baseline evidence for #167. It does not authorize CI or test changes. Full cross-platform node-ID parity, frontend/Windows case counts, billing, per-test timing, and fixture setup/teardown costs remain unmeasured. The safe next step for #168 is to compare test ownership, fixture dependencies, and assertion intent across the listed candidate clusters while preserving tenant isolation, RBAC/auth, immutable audit, CAS, migrations, Supplier Quotes, and document-provenance coverage. No test deletion or weakening is recommended.
