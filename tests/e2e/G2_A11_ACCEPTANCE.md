# A11 local product acceptance

Candidate for Issue #133; product certification and integration remain pending. Live baseline independently verified before freeze: `387a8d1d630d4245cdc77b886aafa137cf755515`, exact-main CI #614 / run `37479177837`, completed/success. A10 / Issue #131 is CLOSED/CERTIFIED by comment `6019045198`; PR #132 is merged. A9 D1–D12 is accepted by comment `6011401776`.

## Results

- T0/T1: 56 frontend test files, 446 tests PASS, including new strict adapters, category forms, human dispositions, command recovery/negatives, token-bound dialogs, exact target paging and canonical tabs, plus existing Asset Review/Workbench/grid/draft/overview/session regressions.
- T2: frontend lint/type PASS; production build and bundle marker guard PASS; npm audit reports zero vulnerabilities. Existing Vite size warning remains (about 770 kB minified / 212 kB gzip). Backend and browser-runner Ruff PASS; 107 real PostgreSQL price-evidence authority/API/projection/concurrency/storage tests PASS, with existing deprecation warnings. No dependency or workflow changes.
- T3: `run_g2_a11_live.py` completed with exit 0 on synthetic project `8612bf15-706b-4209-84c5-a9e5c47edbe4`, organization `a11-acceptance-v6`, three sealed lines, migrated PostgreSQL 16, MinIO, FastAPI, Vite and Chrome. It uses real APIs and browser forms. The recovery fault aborts a response after an actual backend commit; it never supplies a fabricated business response.
- Accessibility: `run_g2_a11_accessibility.py` completed with exit 0 on synthetic project `f4752ccb-ce01-4703-a5fb-3afa6437f5cd`. Real Fluent tabs support arrows/Enter; Field errors expose `aria-invalid` and associated validation text; 50 forward/backward modal focus checks passed; Escape returns to modal and drawer triggers. No evidence command was submitted in this runner.

## Browser matrix

| Required case | Actual evidence |
| --- | --- |
| 1. Current Workbench COMPLETE → PRICE_EVIDENCE Next Action | Existing overview action returns to Workbench; evidence POST count unchanged |
| 2. Exact deficient line and focused price tab | Server context `line_id` selected; accessible tab selected/focused. Later-page loading separately proven in component test |
| 3. First-use boundary | Four canonical tabs; no legacy final-price panel; zero sources and zero qualifying coverage |
| 4. Internet source | Real registration retains synthetic text/provenance/decimal value and HTTPS reference; zero remote-reference requests; registration alone covers zero lines |
| 5. Explicit acceptance | One exact line decision yields server coverage 1/3 |
| 6. Shared source | Second and third lines remain uncovered until their separate relationship/decision commands |
| 7. Full sealed coverage | Fresh server workspace reports 3/3; all exact line identities present in separate requests |
| 8. Whole-set confirmation | Explicit modal and A10 full-set CAS command succeeds |
| 9. Fresh COMPLETE | New Case State reports PRICE_EVIDENCE COMPLETE |
| 10. Downstream hold | `NO_AUTHORIZED_DOWNSTREAM_ACTION`; no A11 supplier/final-result action |
| 11. Optional working price | All official `appraised_unit_price` values remain null while PRICE_EVIDENCE is COMPLETE |
| 12. Correction and withdrawal | Source successor removes prior coverage; exact relationship withdrawal later removes one line. History retained; no silent reconciliation |
| 13. Reconfirmation | Three explicit successor decisions and reasoned set confirmation restore COMPLETE |
| 14. Confirmation withdrawal | Non-COMPLETE with qualifying 3/3 retained; reason mandatory |
| 15. CAS conflict | Real concurrent registration makes the open modal's request return one 409; fresh reads and no replay |
| 16. Unknown outcome | Real confirm commits, response is dropped; reload retains original UUID; explicit scoped receipt lookup then fresh current reads recover COMPLETE |
| 17. Access/session/non-DRAFT | Owned session closed through existing API: 404 and unavailable write controls. Existing archive API: new command 400, COMPLETE remains read-only. Viewer command 403; out-of-scope read 404 |
| 18. Keyboard/focus | Real Fluent dialog trap, explicit controls, labelled fields/error association, tab arrows/Enter and predictable Escape return |

Both additional categories were registered through their real forms: explanation selects a registered source and submits exact decimal coefficient/method; historical source selects readable same-tenant project and exact line labels, then retains a result transcription. Historical fixture lineage is A10 manual transcription, not APPRAISAL_RESULT certification. An explicit relationship withdrawal and successor acceptance were also exercised.

## Visual evidence

Nine candidate PNGs at 1440×900 are in `evidence/g2_a11/`, including first use, one accepted line, COMPLETE/hold, stale successor, conflict recovery, receipt recovery, non-DRAFT and the whole-set reconfirmation dialog. `browser-evidence.json`, `accessibility-evidence.json` and `capture-manifest.json` record fixture identities, checkpoints, command IDs, source blob hashes, image hashes and comparison authorities. No protected reason/source material or credentials are stored in command logs; shown content is synthetic.

Manual QA compared the approved S13 drawer and accepted A8 Workbench shell/grid. Canonical four-tab composition, right contextual drawer, Fluent light tokens and the existing table remain consistent. The original `03` screenshot was rejected because the modal was not visible; it is excluded from the package. The replacement `10` capture explicitly waits for the modal and disables screenshot-time animation. Approved baselines are unchanged. The external freeze manifest and Draft PR bind the exact reviewed commit to the implementation blob hashes captured here, avoiding a self-referential commit SHA.

## Reproduce and limits

Use a disposable migrated database and object-storage bucket. Set the existing `POSTGRES_*` and `S3_*` variables, start the backend at 127.0.0.1:8000 and Vite at 127.0.0.1:5173. Run `bootstrap_g2_a5.py` from backend with `PYTHONPATH` pointing to backend, a test-only `A5_SYNTHETIC_PASSWORD` and a fresh `SYNTHETIC_ORGANIZATION_SLUG`; it uses the established guarded intake/Apply fixture and migrated standard roles. Supply its UUID/slug as `A11_PROJECT_ID`/`A11_ORGANIZATION_SLUG`, plus `A11_SYNTHETIC_PASSWORD` and `A11_EVIDENCE_DIR`; run `python tests/e2e/run_g2_a11_live.py` with Playwright and Chrome available. Use a new fixture for each full run: histories are immutable and the negative case archives the synthetic project. Run the accessibility script on a DRAFT fixture with current upstream proof and available registration; a reconfirmable fixture additionally captures the modal without submitting it.

The three-line browser fixture fits the first page. The exact target outside the initial page is exercised deterministically with the real Workbench composition and mocked paginated reads, not claimed as live paging evidence. Historical selection demonstrates safe lineage/transcription only. Existing shell navigation and comparative/legacy grid columns are preserved baseline surfaces; A11 does not promote their data into evidence authority or add downstream actions. Full OS-G2 remains PARTIAL; no migration, write family, RBAC, membership, supplier/final-result, provider, deployment or release authority changes.

Both independent reviews and exact-head repository CI must address one frozen clean commit. Any source change invalidates those results. Draft PR only, `Refs #133`; Gate Owner owns Ready, guarded squash merge, exact-main CI, product certification and Issue closure.
