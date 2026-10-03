# Valora OpenViking Operating Profile v1

OpenViking is NOT part of Valora product runtime. It supports Codex Desktop development as optional memory, retrieval and development skill storage. It is never a backend, frontend, production-service, customer-data, Case State, Workbench or product-knowledge dependency.

## Authority and invariants

Live GitHub/repository, relevant CODEX, accepted scoped ADR and current task authority govern implementation in CODEX's existing precedence. Codex is the implementation engine; OpenViking is NON-AUTHORITATIVE acceleration only.

| Rule | Operating requirement |
| --- | --- |
| OV-1 | Live repository/CODEX/accepted ADR/current task authority always outranks memory. |
| OV-2 | Verify main SHA, PR HEAD/state, CI, Issue state, migration head, changed files and worktree state live. Memory cannot certify them. |
| OV-3 | Complete live authority bootstrap before recall. Ignore pre-bootstrap injected memory as authority. |
| OV-4 | Find/search → small context → targeted read; no default bulk loading. |
| OV-5 | Aggregate returned recalled context per bounded task: ≤600 tokens by default; ≤1000 for high-context resume/debug. Justify a larger budget explicitly before retrieval. |
| OV-6 | Persist durable certified lessons only; never volatile task state. |
| OV-7 | Never persist secrets, real customer/client data, PII, production payloads or real appraisal values. |
| OV-8 | Failure/outage → continue the [Lean Protocol](VALORA_LEAN_AGENT_PROTOCOL_V1.md); memory is never a prerequisite. |

## VALORA_LEAN_MCP

| Capability | v1 default |
| --- | --- |
| Manual MCP recall and targeted read | ON when useful, after bootstrap |
| Manual durable remember | ON only under persistence rules |
| Automatic per-prompt recall | OFF |
| Automatic transcript capture, extraction or replay | OFF |
| Automatic profile/context/archive injection | OFF |
| Full automatic memory plugin behavior | OFF |

Keep native local skill discovery available. Loading a relevant local skill is distinct from semantic memory recall or transcript capture. Do not enable global automatic recall/capture for this profile.

## Installed integration discovery

Discovery on 2026-10-03 used the installed OpenViking Memory Codex plugin `0.10.5`, its README, `hooks/hooks.json`, `scripts/config.mjs`, `scripts/shared/config-schema.mjs`, lifecycle scripts and the actual session tool inventory. This is a dated capability observation, not evergreen state certification.

- Both `mcp__openviking__*` and `mcp__openviking_memory__*` expose: `health`, `find`, `search`, `read`, `list`, `tree`, `glob`, `grep`, `remember`, `write`, `edit`, `forget`, `add_resource`, `list_watches`, `cancel_watch`. Treat these as two routes, not two independent authorities. Health succeeded.
- No `add_skill` is exposed in this session and no `ov` CLI is on PATH. The installed skill documentation describes `add_skill(data=...)` and `ov skills add`, but neither can be assumed available. Do not use `write`, `edit` or `add_resource` as substitute skill registration.
- Codex supports native repository-local `.agents/skills/<name>/SKILL.md`, also documented in the installed OpenViking `openviking-skills` migration section. Required YAML frontmatter: `name`, `description`; Markdown body follows. See [official Codex skill documentation](https://learn.chatgpt.com/docs/build-skills). This is Codex filesystem discovery, not OpenViking server registration.
- Native discovery exposes name/description; relevant bodies load on invocation. Restart/reload a Codex session rooted in this worktree if its skill snapshot predates these files. Explicitly invoke `$valora-…` or read the exact local SKILL.md as the fallback. No server is needed.
- External OpenViking skills, when supported, use `viking://~/skills/<name>/SKILL.md` or shared `viking://agent/skills/...`. `find(context_type="skill")`/`read` provide explicit discovery; the plugin can also inject a catalog at SessionStart. External registration was not performed or claimed for v1; six local canonical skills are sufficient.
- Before profile launch, effective settings in the chat's parent workspace were `enabled=true`, `autoRecall=true`, `autoCapture=true`, `autoCommitOnCompact=true`, `noAutoInject=false`, `resumeArchiveInject=true`. A pre-bootstrap memory block was observed. Automatic recall was active; automatic capture was configured active, but no claim is made that a specific transcript upload succeeded.
- Available MCP responses expose no dedicated usage/embedding/compression billing telemetry tool. Record any actual usage fields returned; otherwise use `N/A (not exposed)`, never zero. See the [pilot](VALORA_OPENVIKING_TOKEN_PILOT_V1.md).

## Enforcing manual mode and fallback

The installed plugin supports [workspace schema v1](../../.openviking/config.json): `recall.enabled=false`, `capture.enabled=false`, and `bypass.session_patterns=["**"]`. These suppress workspace recall/capture and session injection. Environment, machine registry and private local overrides may outrank the committed settings; inspect effective settings on each environment.

Workspace settings alone are insufficient for a strict no-capture guarantee: installed SessionStart can replay pending writes/sweep prior sessions even when bypassed, and PreCompact has a separate gate. Therefore use [Start-ValoraLeanCodex.ps1](../../scripts/tooling/Start-ValoraLeanCodex.ps1) for a fresh process:

```powershell
Set-Location '<assigned Valora worktree>'
./scripts/tooling/Start-ValoraLeanCodex.ps1
# Inspect only, without launching:
./scripts/tooling/Start-ValoraLeanCodex.ps1 -CheckOnly
```

The launcher temporarily sets `OPENVIKING_MEMORY_ENABLED=0`, `OPENVIKING_AUTO_RECALL=0`, `OPENVIKING_AUTO_CAPTURE=0`, `OPENVIKING_AUTO_COMMIT_ON_COMPACT=0`, `OPENVIKING_NO_AUTO_INJECT=1`, `OPENVIKING_RESUME_ARCHIVE_INJECT=0`, `OPENVIKING_SKILL_CATALOG=0`, and `OPENVIKING_RECALL_COMPRESS_DETECT_ON_STARTUP=0`. It restores the invoking shell's process environment afterward. The master lifecycle gate prevents SessionStart sweep/replay, recall, capture, compact and end processing. The installed MCP proxy does not consult that lifecycle `enabled` switch; manual tools retain their credential resolution. No credentials belong in these committed files.

Validation against installed `0.10.5`: all five lifecycle hooks exited without context against an unreachable loopback endpoint under these switches; the actual MCP proxy still served `tools/list` and `health`. Native Codex app-server `skills/list` with this worktree and force reload discovered all six canonical skills, and all six bodies were readable and passed the bundled skill-creator validator (Python UTF-8 mode on Windows). These checks validate this installed build; repeat discovery after integration upgrades.

For Desktop, either disable this plugin's lifecycle hooks through the supported hook controls while retaining its MCP, or fully exit Desktop and start its actual executable through this launcher using `-Executable <installed Desktop executable>`. A pre-existing Desktop process may retain old environment settings. Verify a fresh session has no automatic memory injection and hooks are disabled before claiming compliance. The launcher default starts Codex CLI, not Desktop; this PR does not claim to reconfigure an already-running Desktop chat. Do not edit plugin cache or global preferences as a substitute.

If manual MCP is unavailable, times out, or errors, record the unavailable call once and continue Lean with current repository files and local skills. Do not retry indefinitely, reconstruct state from memory, install a product dependency or wait for server recovery. Disable the optional plugin/MCP connection through Codex controls if repeated connection attempts interfere with work. Normal Git/CODEX/task verification remains available offline from OpenViking.

## Recall decisions and budget control

Do not recall by default for tiny mechanical corrections, acceptance reconciliation, whitespace/CI fixes, straightforward CODEX edits, an exact-pattern migration or an obvious one-file fix. Prefer recall for dirty-worktree resume, recurring RBAC/migration/provenance failures, concurrency/debug history, similar reviewer findings or multi-session debugging. Consider recall before reading more than five historical docs or reconstructing history.

After live bootstrap, state the retrieval question. Request one or a few ranked abstracts via `find`/`search`; inspect relevance, then read only the needed record. Restrict to the project or exact URI where supported. Count ALL returned memory text, envelopes and abstracts, not merely the summary quoted in the answer, against the task budget. Use the actual model tokenizer when available; otherwise label the estimate and reserve headroom. Stop further retrieval at the limit. A full read without a response cap can overshoot: prefer compact records, inspect abstracts first, and record any overrun and justification rather than pretending the excess was free. Do not confuse the auto-hook budget knobs with a manual MCP response limit.

## Persistence and privacy

Allowed kinds: `engineering-pattern`, `failure-lesson`, `process-rule`, `architecture-hint`. Normally keep records approximately 100–300 tokens. Persist only after task certification, a proven reusable failure lesson, or acceptance of a stable operating rule. Review the exact payload and source before manual remember. Registration of a skill is optional external storage under the same privacy boundary.

Never persist passwords, API keys, GitHub tokens, DB credentials, secret-bearing connection strings, cookies, private keys, production payloads, real customer/client data, PII or real appraisal values. Use synthetic examples and references to public certified evidence. Automatic capture is not made safe merely by regex redaction.

Do not remember current main SHA/HEAD, CI status, PR state, active Issue number as durable truth, changed-file/worktree state, Draft hypotheses, unresolved findings or pending PO decisions. Do not copy entire CODEX/ADR files, project history, large diffs, full CI logs or review dumps. A source reference may identify immutable certified evidence; it must not assert it is the current state.

```text
VALORA MEMORY
Kind: <allowed kind>
Subject: <reusable topic>
Lesson: <compact proven rule and preconditions>
Source: <certified task or proven failure evidence>
Source reference: <immutable evidence link and relevant section>
Authority: NON-AUTHORITATIVE MEMORY
Verification rule: Re-read current live implementation/authority before use.
Invalidation: Ignore when current repo/CODEX/ADR contradicts this memory.
```

## Six-skill catalog

Canonical sources are committed native Codex skills; they neither depend on nor register themselves into OpenViking.

| Skill | Source | Purpose |
| --- | --- | --- |
| valora-live-authority-bootstrap | [SKILL.md](../../.agents/skills/valora-live-authority-bootstrap/SKILL.md) | Live fetch, authority, exact CI/task and readiness |
| valora-dev-handoff | [SKILL.md](../../.agents/skills/valora-dev-handoff/SKILL.md) | Mandatory CODEX MODEL block on every Dev prompt |
| valora-worktree-resume | [SKILL.md](../../.agents/skills/valora-worktree-resume/SKILL.md) | Read-only inspection, live verification and reviewed checkpoint |
| valora-high-risk-gate-review | [SKILL.md](../../.agents/skills/valora-high-risk-gate-review/SKILL.md) | Frozen HEAD, independent gates and guarded integration |
| valora-postgresql-proof | [SKILL.md](../../.agents/skills/valora-postgresql-proof/SKILL.md) | Real DB concurrency, migration, tenant and atomic proof |
| valora-integration-closeout | [SKILL.md](../../.agents/skills/valora-integration-closeout/SKILL.md) | Exact-main certification and next authorized slice |

Every Dev/Codex handoff, including tiny continuation, reviewer/evidence/CI corrections and acceptance reconciliation, must BEGIN with `CODEX MODEL`, exact `Model`, `Reasoning`, `Selection reason` and `Escalation`. Missing routing is INVALID; vague agent labels do not substitute. The handoff skill defines the full block and routing guidance.

Optional future external registration requires the actual `add_skill` tool or `ov skills add` to become available. Validate canonical frontmatter, check each target for collision, register the exact reviewed SKILL.md content, then list/find/read all six and compare retrieved content against Git. Confirm before replacing existing user/shared skills. Keep Git sources usable without the server; do not store volatile evidence as memory. This optional procedure is not a v1 prerequisite.

## MCP usage block

```text
OPENVIKING PROFILE
Mode: VALORA_LEAN_MCP
Authority: OpenViking is NON-AUTHORITATIVE.
Live repository/CODEX/task authority always wins.
Usage: After live bootstrap, use OpenViking only when prior project experience can materially reduce repository reading.
Prefer: find/search → small context → targeted read.
Default recall: <=600 tokens total returned context per bounded task.
High-context resume/debug: <=1000 tokens unless explicitly justified.
Do not reconstruct live state from memory, bulk-load memory, store secrets/client data or persist volatile task state.
Persist: durable certified lessons only.
Fallback: If OpenViking is unavailable, continue with Lean Protocol.
```

## Measurement and future automatic memory

The [six-observation pilot](VALORA_OPENVIKING_TOKEN_PILOT_V1.md) compares Lean-only A with manual-MCP B. Measure main input/output and available server/embedding/compression usage separately, retrieval volume, repository reads, time, findings and rework. The target is ≥20% lower main input for comparable Medium/High tasks without more material findings or rework. No savings are claimed before evidence exists; unavailable telemetry prevents a total-cost claim.

Mode C/automatic recall/capture remains OFF throughout v1. A future phase requires explicit authority, measured pilot results, reviewed privacy/retention and workspace isolation controls, verified hook behavior, bounded budgets and a tested disable/fallback path. A favorable pilot does not itself authorize automatic capture or product/runtime integration.
