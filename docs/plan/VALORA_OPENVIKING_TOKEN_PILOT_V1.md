# Valora OpenViking Token Pilot v1

Status: PLAN ONLY — no observations collected and no token/cost savings claimed. Use the [operating profile](VALORA_OPENVIKING_OPERATING_PROFILE_V1.md) after live authority bootstrap.

## Design

Six future task observations: two Low/mechanical, two Medium/integration, two High-context/resume/debug. Within each stratum assign one task to A (Lean only) and one to B (Lean + manual MCP), before work begins. Low tasks may correctly have zero MCP calls. Mode C/automatic recall and automatic capture are OFF throughout the pilot.

Match each pair's scope, acceptance complexity, model/effort, initial context, cache conditions and review gates as closely as practical. Record differences; six distinct tasks are a small observational pilot, not a causal benchmark. Do not rerun the same solved task with a warmed agent and label it a fair A/B comparison. Use a fresh task session, with the profile's hook controls verified, and include all continuations/reviewer fixes in that task's main usage totals.

| Observation | Stratum | Mode | Task/evidence | Status |
| --- | --- | --- | --- | --- |
| L-A | Low/mechanical | A | Pending | Not measured |
| L-B | Low/mechanical | B | Pending | Not measured |
| M-A | Medium/integration | A | Pending | Not measured |
| M-B | Medium/integration | B | Pending | Not measured |
| H-A | High-context/resume/debug | A | Pending | Not measured |
| H-B | High-context/resume/debug | B | Pending | Not measured |

## Per-task ledger

Keep task evidence in the approved task artifact location; never persist this volatile ledger to OpenViking as durable truth. No transcript, secret or client payload is required for measurement.

| Field | Measurement/source |
| --- | --- |
| Task, stratum, A/B, model/effort, baseline, candidate | Live task record; exact SHA is evidence only |
| Main Codex input tokens | Sum actual per-turn usage deltas, including cached input as input; also record cached tokens separately if exposed |
| Main Codex output tokens | Actual usage deltas, including reported reasoning tokens consistently; state provider accounting convention |
| OpenViking returned context tokens | Tokenize complete returned payloads, abstracts and wrappers with main model tokenizer; otherwise mark estimate/method |
| OpenViking server LLM tokens | Actual usage fields or server metrics if available; otherwise N/A (not exposed) |
| Embedding tokens | Actual usage/metrics if available; otherwise N/A (not exposed) |
| Compression tokens | Actual usage if compression occurred; 0 only if verified absent, otherwise N/A |
| Repository search calls | Count rg/search operations consistently, including searches inside batched calls |
| Full-file reads | Count each distinct read operation, including repeated reads; separately count bounded excerpts |
| Elapsed task time | Start/end timestamps in Asia/Saigon and elapsed duration; record external wait time separately |
| Material findings P0–P3 | Independent review counts by severity and affected scope; record advisory findings separately |
| Rework rounds | Each material correction cycle after candidate/review, under the same definition for A/B |
| OpenViking calls | Count successful and failed calls, including health/find/read, and annotate purpose |
| Recall budget/overrun | 600 default or 1000 high-context; justification, measured returned total |
| Missing telemetry/confounders | N/A reasons, scope/model/cache/context/gate differences |
| Certification | Review verdict and exact CI evidence when completed |

Use Codex session usage when accessible. Cumulative snapshots require subtraction from the task's start snapshot; do not sum repeated cumulative totals. If actual main usage is unavailable, mark the observation unmeasurable for the savings target; a character estimate cannot establish measured Codex input savings. Redact unrelated sensitive content from any evidence export.

The installed MCP inventory has no dedicated usage tool. Manual responses may expose usage in some server versions; inspect actual fields rather than inventing metrics. Local tokenization estimates returned text only; it does not measure hidden server LLM or embedding work. Recalled context is already included in main input: show it separately without adding it to main input a second time.

## Evaluation

For each comparable Medium/High pair: `input reduction = 100 × (A_input − B_input) / A_input`, with A_input > 0 and actual usage available. Report each pair and the combined comparable M/H totals. Target ≥20% reduction, with no increase in material findings P0–P3 or rework rounds. Missing/incomparable observations are inconclusive and require another bounded pilot, never an assumed PASS.

Report output, elapsed time, searches and reads alongside input savings. Main-input improvement alone does not prove total-token/cost savings. Report server LLM, embedding and compression costs separately with provider/model pricing dates only when measured; missing cost telemetry blocks a total-cost assertion. Reviewer usage may be recorded separately to assess review cost, without mixing it into main-agent tokens.

After six certified observations, Gate Owner evaluates evidence and confounders. Low tasks using no memory are acceptable. Keep manual mode if results are inconclusive or quality/rework worsens. Any automatic-memory trial needs a separately authorized phase and privacy review; v1 evidence never enables Mode C automatically.
