# A11 PRICE_EVIDENCE product candidate

This is the bounded implementation candidate for [Issue #133](https://github.com/Reguluspt/valora-engineering/issues/133). A10 backend/domain/provider/API was certified at PR #132, merge `387a8d1d630d4245cdc77b886aafa137cf755515`, exact-main CI #614 / run `37479177837`, [comment 6019045198](https://github.com/Reguluspt/valora-engineering/issues/131#issuecomment-6019045198). A9 D1–D12 remains unchanged. A11 product certification, Ready, integration and closure belong to the Gate Owner. Full OS-G2 remains incomplete; SUPPLIER_QUOTES+ remains unauthorized.

## Product surface and authority

The existing Workbench hosts a project-scoped region and the existing Asset Context hosts the exact selected line's evidence workspace. Its four accessible Fluent tabs are `Tổng quan | Thông số kỹ thuật | Nguồn giá & Chứng cứ | Lịch sử`. Validation appears in the selected asset's overview. The former quote/appraised-price panel presentation is replaced; downstream records and API/domain implementations are preserved.

The frontend consumes shared Case State v5 and `price_evidence_confirmation_v1`. Only the exact PENDING `price_evidence_prepare_required` / `price_evidence_preparation` contract routes to Workbench. A coherent safe context selects the exact deficient line, progressively requests additional grid pages, opens Asset Context and focuses the price tab. Navigation submits no evidence command. Completed upstream regions remain available in a keyboard-accessible disclosure when the server's current stage is PRICE_EVIDENCE.

The new read-only `GET /projects/{project_id}/price-evidence/workspace` requires existing scoped `project:read`. Optional `line_id` must belong to the sealed set; source-head pages are capped at 50. It maps the existing authority resolver's qualifying sets, holds, revisions, decisions, withdrawals and confirmation facts. Eligibility uses the existing preparation and source eligibility functions. It adds no persistence, migration, permission, mutation family, state enum or completion/currentness algorithm. Case State and Next Action receive no retained source text, URL, price or rationale. Full material is obtained exclusively through A10's explicit audited source-read endpoint.

The region displays the five server results, safe coverage, confirmation currentness and available whole-set actions. The workspace displays current source metadata, exact relationship/decision identity, server qualifying/hold flags and deadlines. Historical source material can be read through predecessor revision links. React does not count qualifying sources, compute coverage, reconcile revisions or infer COMPLETE. COMPLETE continues to display `NO_AUTHORIZED_DOWNSTREAM_ACTION`; the A11 surface exposes no supplier/final-result CTA.

## Explicit user actions

Internet survey uses retained plain text, explicit provenance/date or unknown-date explanation, observation time, optional expiry, exact decimal strings and value qualifiers. Its public HTTPS reference is displayed as text; there is no remote fetch, link preview, scrape or redirect handling.

Unit-price explanation selects current eligible registered sources by readable origin/revision, records coefficients, assumptions and calculation narrative, and submits A10's exact `sum_of_scaled_source_values` method. The server checks arithmetic and professional suitability remains an explicit human decision. No working price is read into or written by this flow.

Prior appraisal-result evidence uses existing bounded same-tenant project and exact asset selectors. The user transcribes the historical date, retained result excerpt, locator, currency/unit and decimal result value. This preserves A10's retained historical transcription contract; it does not assert that an existing Project/line is a certified APPRAISAL_RESULT record. Supplier quotations cannot supply this category's authority.

Each human relevance decision explicitly names one selected asset and source revision. It collects source portion, line relevance, suitability, limitations, temporal applicability, priority considerations and a finite review deadline. Shared sources require separate commands and decisions for every line. Negative decisions and successor decisions require reason notes. Corrections append a source successor; source/relationship/decision withdrawals target exact server-permitted identities and preserve history. Unresolved concerns remain server-derived and require explicit successor decisions.

Whole-set confirmation binds the full current sealed set and all exact line versions, including rows outside the displayed page. Reconfirmation and confirmation withdrawal require the exact prior/current confirmation and a nonblank reason. These actions neither finalize an appraisal result nor reset working prices, membership or upstream proof.

## Failure and recovery

The typed adapter constructs only each A10 contract's fields, with project/seal/set/membership/Workbench/full-line CAS and one command UUID. Recovery identity is persisted in session storage scoped to actor and project before dispatch. Storage failure prevents dispatch. Actor/project changes hide prior scoped data and cannot adopt another scope's recovery command.

Transport failure or 500 retains that UUID and blocks other evidence mutations. `Kiểm tra kết quả thao tác` explicitly looks up the original scoped historical receipt, checks actor/project/command/contract scope, then refreshes Case State, preparation and workspace. A receipt never marks current completion. Missing receipts require renewed explicit user confirmation after successful refresh; failed receipt/current reads retain recovery. There is no blind retry or automatic replacement UUID.

400 and 409 refresh authority without replay. 401/403 and cross-scope 404 clear protected displays and fail closed. A background read error keeps usable prior data visible with writes disabled. Coherent current read results must share a Case State token; older upstream tokens or mismatched selected lines disable writes. Dialogs survive harmless same-token refreshes, disable submission while reads run, and close when their authoritative token changes or access is lost. Non-DRAFT current COMPLETE can remain readable while server eligibility disables official writes.

## Verification and delivery

Focused tests cover adapter request construction, hook recovery and negatives, category forms, human disposition mapping, exact target paging/focus and canonical tabs. Backend projection tests exercise real PostgreSQL authority, safe disclosure, independent per-line coverage, revision/hold mapping, paging, access and non-DRAFT reads. Existing full frontend tests provide Asset Review, Workbench, grid, Human Commit, overview, session and drawer regression coverage.

`tests/e2e/run_g2_a11_live.py` uses the migrated local PostgreSQL/MinIO/API/browser stack with synthetic fixtures created through existing intake/guarded-Apply conventions. Upstream review/Workbench and A11 actions use actual APIs and browser confirmations. Its one network fault aborts the response only after a real confirm commits; it never fabricates a business result. Synthetic historical selection tests A10 transcription and lineage, not historical final-result certification. No approved screenshot baseline is overwritten.

Candidate screenshots, checkpoint JSON, tests, exact changed-file hashes, both independent reviewer transcripts/adjudication and exact-head CI results are recorded with the Draft PR. The checked-in evidence package describes viewport, fixtures and comparison authorities. No local evidence or Draft PR certifies product closure. Any reviewed HEAD change requires new reviews and exact-head CI.
