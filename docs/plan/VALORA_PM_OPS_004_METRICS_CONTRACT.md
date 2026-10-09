# PM-OPS-004 metrics contract v1.0

**Status:** #159 candidate tooling contract; certification belongs to Gate Owner. **Date:** 2026-10-09. **Scope:** offline sanitized metadata only, parent [#158](https://github.com/Reguluspt/valora-engineering/issues/158); no provider calls, transcript extraction, runtime or other PM-OPS-004 work.

Authority: [CODEX §§8.1,10.1–10.4](../../CODEX.md), [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md), [Protocol v2](VALORA_AGENT_OPERATING_PROTOCOL_V2.md), [Compact Task Contract](VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md), [Dev Handoff](../../.agents/skills/valora-dev-handoff/SKILL.md), [#159 handoff](https://github.com/Reguluspt/valora-engineering/issues/159#issuecomment-6073084627), and its [limited routing-evidence exception](https://github.com/Reguluspt/valora-engineering/issues/159#issuecomment-6073337098). Baseline main `9fc35fbd92758c28bc7b54351d9c6efb52194d89`, CODEX blob `de7e47d224a4f90bc190c182638d6a55c17540e5`, exact-main CI #649/run 37864462434 SUCCESS 5/5. These identify task origin; live validation still governs candidate freeze.

Requested implementing route `gpt-6.1-sol / medium` was accepted, task `/root/sol_implementer`; actual executing model/effort UNVERIFIED and native session UUID NOT EXPOSED. The child authors and adjudicates; parent performs coordination and deterministic Git/checks. This exception supplies no actual-model attribution, billing measurement or gate certification.

## Input boundary and schema

[`scripts/valora_llm_usage_audit.py`](../../scripts/valora_llm_usage_audit.py) uses Python standard library (3.12+), without network, directory discovery, environment/credential access, Git commands or provider requests. Its sole source is one explicitly chosen regular `.json`/`.jsonl` file, UTF-8, at most 2,000,000 bytes and 2,000 events. It rejects symlink input, duplicate JSON keys, unexpected fields at every object boundary, malformed or unbounded values, and unsupported versions. This is a sanitized metadata importer, not a native log sanitizer: prepare exports separately without ever feeding raw transcripts to it. A supplied sanitation flag/provenance reference is an assertion, not independent authentication. Deliberately encoded private data cannot be detected by schema validation; supply only reviewed synthetic/sanitized exports.

JSON envelope has exactly `schema_version: "1.0"`, `sanitized_metadata: true`, `events: [event, ...]`. JSONL has one envelope per nonblank line with exactly `schema_version`, `sanitized_metadata`, `event`. All event fields below are required; nullable values express unavailable evidence. Missing counters remain null rather than zero. `usage` may contain only fields named for its adapter, with nonnegative integers ≤10^15 or null. Unknown keys, even if apparently harmless, block the entire input; no partial success or quarantine artifact is emitted.

| Event field | v1 constraint and meaning |
| --- | --- |
| `event_id` | `e-` plus eight lowercase hex characters; unique within input; sanitized local identity |
| `task_id` | `VALORA-TASK-` plus 1–100 uppercase letters/digits/hyphens; task identity |
| `issue`, `pr` | Positive integers; exact historical/candidate references, not gate status |
| `base_sha`, `candidate_sha` | Exact 40 lowercase hex Git commits; never blob IDs or `main` aliases |
| `packet_sha256`, `packet_bytes` | Exact 64 lowercase hex digest and positive UTF-8 byte count; distinct from tokens |
| `provider` | `openai`, `deepseek`, `google`, or `UNKNOWN`; unknown runner identity warns |
| `model` | Closed supported labels: `gpt-6-luna`, `gpt-6-astra`, `gpt-6.1-sol`, `deepseek-v4.1-flash`, `opencode-go/deepseek-v4.1-flash`, `gemini-3.1-pro-high`, `UNKNOWN` |
| `model_identity` | `NATIVE_REPORTED` or `ACTUAL_MODEL_UNVERIFIED`; requested label is never proof of actual model |
| `session_id` | Sanitized opaque letters/digits/underscore/hyphen, 1–128 characters; report retains only SHA256 pseudonym |
| `phase` | `preflight`, `review`, `implementation`, `adjudication`; no implied agent authority |
| `attempt`, `sequence` | Positive bounded integers; sequence unique and ordered within task/provider/session stream |
| `timestamp` | Valid UTC ISO8601 with `Z`, up to six fractional digits; strictly increasing by instant in each stream |
| `snapshot_kind` | `per_turn`, `cumulative`, `delta`; counter source semantics, never guessed from growing values |
| `origin` | Per-turn null; cumulative initial `ZERO`/`UNAVAILABLE`, subsequent exact predecessor event ID; source delta exact sanitized origin ID |
| `usage_format`, `usage_source` | Adapter below; provenance `SYNTHETIC` or public `https://github.com/Reguluspt/valora-engineering/(pull|issues)/N#issuecomment-N`; no arbitrary URL/path/free text |
| `usage` | Allowlisted counters only; no prompt, response, message, reasoning content, tool arguments, source text, price data or credentials |
| `finish_reason` | `stop`, `length`, `STOP`, `MAX_TOKENS`, `completed`, `incomplete`, `UNKNOWN`, `content_filter`, `SAFETY`, `error`, `tool_calls` |
| `report_state` | `COMPLETE`, `INCOMPLETE`, `NOT_APPLICABLE`, `UNKNOWN`; report content not accepted |
| `quality` | `REPORTED_PASS`, `REPORTED_FINDINGS`, `NOT_EVALUATED`; a source claim, never script adjudication or certification |
| `elapsed_ms` | Nonnegative integer or null; source-reported duration, not inferred from token counts |
| `cost` | Null, or exact object `amount`, `currency`, `source`, `original_charge`; rules below |

Task-wide Issue/PR/base/candidate/packet digest/bytes must agree even across sessions. Stream model/identity/adapter/source/snapshot kind also cannot change. A changed packet or HEAD requires a separate audited task export; mixing identities blocks. CLI `--expected-head` and `--expected-packet` independently pin the supplied identities. The CLI cannot prove a claimed SHA is a commit or recompute packet bytes/digest because it never reads source packets or Git; use separately verified metadata. Hashes are asserted provenance, not cryptographic attestation of model or content.

## Provider field maps

API maps describe official API usage objects exported into flat sanitized counters. They must never be applied to a runner's counters just because the runner calls that provider. Format asserts the original field provenance. No automatic provider-format guessing occurs.

| Format | Native → report input / cached / cache-write / output / reasoning / total | Cache inclusion |
| --- | --- | --- |
| `deepseek_chat` (`deepseek`) | `prompt_tokens` / `prompt_cache_hit_tokens` / null / `completion_tokens` / `reasoning_tokens` / `total_tokens`; optional `prompt_cache_miss_tokens` validates hit+miss | `INCLUDES_READ`; uncached=input−cache-hit |
| `gemini_generate` (`google`) | `promptTokenCount` / `cachedContentTokenCount` / null / `candidatesTokenCount` / `thoughtsTokenCount` / `totalTokenCount` | `INCLUDES_READ`; uncached=input−cached |
| `openai_responses` (`openai`) | `input_tokens` / flattened `input_tokens_details.cached_tokens` as `cached_tokens` / flattened `input_tokens_details.cache_write_tokens` as `cache_write_tokens` / `output_tokens` / flattened `output_tokens_details.reasoning_tokens` as `reasoning_tokens` / `total_tokens` | `INCLUDES_READ_WRITE`; ordinary uncached=input−cache-read−cache-write, only if both counters present |
| `codex_metadata` (`openai`) | `input_tokens` / `cached_input_tokens` / `cache_write_input_tokens` / `output_tokens` / `reasoning_output_tokens` / `total_tokens` | `UNKNOWN`; native counter values preserved, uncached unavailable |
| `runner_metadata` (any declared provider) | `input` / `cached` / `cache_write` / `output` / `reasoning` / `total` | `UNKNOWN`; no inferred inclusion/exclusion or uncached |

Official references verified on 2026-10-09: [DeepSeek Chat Completions usage](https://api-docs.deepseek.com/api/create-chat-completion/), [Gemini UsageMetadata](https://ai.google.dev/api/generate-content#UsageMetadata), [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching). DeepSeek input=hit+miss; output includes reasoning. Gemini total includes prompt+thoughts+candidates, so thoughts must not be treated as a subset of candidates. OpenAI output includes nonvisible tokens; reasoning is a subset, not added to output; current cache-write input is separate from cache-read. See [OpenAI token counting](https://developers.openai.com/api/docs/guides/token-counting). Missing any needed component prevents reconstruction. Gemini tool-use prompt counters are outside this bounded adapter; their appearance is rejected rather than silently miscounted.

Inclusive cached tokens must not exceed input; inclusive OpenAI read+write must not exceed input. Available DeepSeek/OpenAI/Codex total must equal input+output, available reasoning cannot exceed output. Available Gemini total must equal input+candidates+thoughts. Missing values are accepted with WARN; no zero fill, visible-output conversion, tokenizer estimate, token ratio, undocumented exclusive-cache conversion or rate lookup. UNKNOWN is an honest supported measurement state, not a parser PASS.

## Cumulative, delta and phase accounting

Per-turn counters are separate additive measurements. Source-reported deltas are additive only within a distinct delta stream, carry a sanitized origin reference and warn `SOURCE_REPORTED_DELTA_NOT_RECONSTRUCTED`: the tool does not claim to have verified the external endpoint subtraction. Duplicate delta origins within a stream block. Do not import those deltas alongside the cumulative stream that produced them. Snapshot-kind mixing in one session blocks. External delta completeness/comparability still requires source evidence; no cost or cross-stream total is manufactured.

Cumulative snapshots form one exact predecessor chain within task/provider/session, regardless of phase or attempt. First `ZERO` asserts a proven zero-session origin: its counters are counted once. First `UNAVAILABLE` is baseline-only; its contribution is null/WARN, while later measured increments remain usable. Every subsequent counter contribution is `current−previous` only if both values exist; otherwise null. Any decreasing counter blocks. Repeated equal snapshots contribute zero and WARN, never double count. Duplicate event IDs or sequence identifiers block. Derived inclusive cache deltas cannot exceed the corresponding input delta. `origin` binds event identity, not nearest timestamp or a guessed phase start.

Increment belongs to the incoming snapshot's phase. Accurate phase allocation therefore requires boundary snapshots: otherwise it is source-reported attribution rather than proven timing. Phase totals are separated by task/provider/session/phase; any unavailable component keeps that aggregate component null. There is no grand total across models/providers/tasks, no matched baseline, ROI or savings. Ordering is deterministic task/provider/pseudonymous-session/sequence/event; shuffling input preserves JSON/CSV bytes.

## Finish, quality, cost and privacy

Review `COMPLETE` requires both terminal finish (`stop`/`STOP`/`completed`) and `report_state=COMPLETE`. `length`/`MAX_TOKENS`/`incomplete`, errors and safety/filter outcomes remain INCOMPLETE even if report state falsely says COMPLETE. `tool_calls`/UNKNOWN cannot establish a complete review. Earlier failed attempts stay visible when a later report completes; no review independence or authority is inferred. Quality is retained as reported evidence and never promoted to Gate PASS.

Absent charge is `NOT MEASURABLE`. Present cost requires nonnegative finite decimal text (≤13 integer/8 fractional digits), three uppercase currency letters, `source=billing-<64 lowercase hex digest>` of separately sanitized billing evidence, and `original_charge=true`. Output says `SOURCE_ASSERTED_ORIGINAL_CHARGE`, preserving original amount/currency/digest without certifying source authenticity or ISO currency membership. Cumulative billing counters are unsupported and block: do not sum overlapping charges. Charges are never summed or compared; phase cost classification is `NOT COMPARABLE`. Tariffs, inferred prices, token discounts, subscription conversions, FX, ROI and monetary savings are unsupported. Missing charge is a warning, not zero dollars.

No freeform content fields are allowed; sessions are pseudonymized; all failures emit only constant error codes, never rejected keys, values, paths or exception messages. Existing input, source and output files are never overwritten. User-selected report destinations are the sole writes; parent directories must exist. Outputs must differ from input and one another, and must not already exist. Validation finishes before output creation; IO failure can leave a partial report file, which must be discarded. The sanitation declaration cannot authenticate safe source selection. Never invoke on raw prompt/private reasoning/transcript/customer/log/credential material, even with a JSON extension. Metadata hash references do not authorize opening original sensitive evidence.

## CLI and verification

From repository root, the following works on Windows PowerShell and Linux (choose new report filenames):

```text
python scripts/valora_llm_usage_audit.py scripts/tests/fixtures/valora_llm_usage_audit/a18_a19.json --json-out summary.json --csv-out summary.csv
python -m unittest discover -s scripts/tests -p test_valora_llm_usage_audit.py -v
```

Without `--json-out`, JSON goes to stdout; CSV is optional with `--csv-out`. Exit 0 means OBSERVED with no measurement warnings; exit 1 means valid report with WARN; exit 2 means BLOCKED with a constant JSON error on stderr and no report for validation failures. No state means certified or Gate PASS. Historical fixture invocation intentionally exits 1 for unavailable fields/costs and incomplete attempts.

T0 covers strict schema/allowlist/adapters/serialization, counter/cache and identity rejection. T1 covers sanitized historical controls, cumulative and phase deltas, shuffled ordering, golden JSON/CSV, JSONL, executable CLI and exit/privacy/output behavior. T2 covers Python compile/lint, unchanged security guard, scope/whitespace/static offline/privacy and reference checks. Product runtime/PostgreSQL/browser T3 is N/A; CLI integration is mandatory. Tests use component-local `scripts/tests` with stdlib `unittest` and `importlib` script loading, following existing `infra/server/tests` tooling convention without changing backend tests/config/CI. Candidate still needs clean frozen HEAD, independent prescribed native review/adjudication and exact-head CI 5/5. Gate Owner alone advances Ready/merges/closes/certifies after exact-main CI.

## Historical baseline controls and limits

These controls are anchored to public sanitized metadata, not comparable cost baselines. Fixture counters other than explicitly listed Luna endpoints are synthetic examples, all identified by `usage_source=SYNTHETIC`; native labels are not a claim this #159 run executed those models.

| Historical control | Observed evidence | Missing / not comparable |
| --- | --- | --- |
| A18 / PR #156 | [Exact-head closeout](https://github.com/Reguluspt/valora-engineering/pull/156#issuecomment-6062165125); no Luna pilot sample in assigned historical control | No Luna event manufactured; no matched A19 baseline or measured billing |
| A19 DeepSeek / PR #157 | [Native report header](https://github.com/Reguluspt/valora-engineering/pull/157#issuecomment-6063998306): two same-session `length` attempts, each 32000 reasoning tokens and no final report; third `stop` completes | Input/cache/output/cost not supplied by this header; fixture's other counter values synthetic |
| A19 Gemini correction | [Native identity-correction evidence](https://github.com/Reguluspt/valora-engineering/pull/157#issuecomment-6063902824): same session, unchanged packet, blob/commit label corrected | Header does not prove cumulative counter values or cache inclusion; synthetic cumulative snapshots exercise conservative runner treatment, not historical token claims |
| A19 Luna preflight vs review | [Sanitized endpoints](https://github.com/Reguluspt/valora-engineering/pull/157#issuecomment-6064034658): preflight input 23822/cached 6912/write 0/output 50/reasoning 28/total 23872; final 408460/357376/0/4359/1021/412819 | Native cache inclusion undocumented here; uncached null; no source charges |
| A19 Luna review-phase delta | Subtract published endpoints: input 384638/cached 350464/write 0/output 4309/reasoning 993/total 388947 | Cumulative total is final endpoint once, never preflight+final; no savings or actual Sol attribution |
| A19 Astra adjudication | [Published adjudication](https://github.com/Reguluspt/valora-engineering/pull/157#issuecomment-6063999338) | No observed tariff/charge; tokens/cost unavailable, not zero |

A19 exact frozen commit `4c8bc37faa892a9b448e9f76a036a2272d89f45c`, base `5b40e376c3efcd9df1321078969df1b71c420433`, packet digest `49256929af7f0c16c7ae9b7949aef7ce0893d0932af2b882c3eeecfb4a4099eb`, bytes 421925 are from the [public manifest](https://github.com/Reguluspt/valora-engineering/pull/157#issuecomment-6063998864). This collector never reads the actual source packet or native transcripts. Fixture aliases/event IDs/timestamps outside Luna endpoints are synthetic and do not pretend to be native identity proofs.
