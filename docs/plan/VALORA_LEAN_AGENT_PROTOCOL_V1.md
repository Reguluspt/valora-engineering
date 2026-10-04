# VALORA Lean Agent Protocol v1

**Lifecycle/status:** SUPERSEDED / HISTORICAL — superseded 2026-10-04 by [Agent Operating Protocol v2](VALORA_AGENT_OPERATING_PROTOCOL_V2.md), the single current general operating-process entrypoint for Gate Owner/Architect and Dev/Codex sessions. The original v1 body below is retained as historical content, including its former budgets/closeout targets; use V2 for current procedure.
**Authority role:** Developer task preparation/execution support only; not product, domain, runtime or deployment authority. Live CODEX, permanent guardrails, accepted scoped authority and the assigned task govern. No product/runtime dependency or new permission is created.

This is an implementation operating protocol, not product or domain authority. [CODEX](../../CODEX.md) and [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md) retain their permanent rules.

## Responsibility split

Gate Owner / Architect interprets project-wide authority, declares risk and issues a [compact task contract](VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md). Codex verifies its baseline, implements the allowed scope, tests and reports. Optional workers handle only bounded mechanical work. Gate Owner controls integration and the next product gate.

## Context and contract

| Tier | Read only when needed |
| --- | --- |
| C0 — start | Contract, exact baseline/CI, applicable permanent rules. |
| C1 — normal | Named authority sections, affected code and tests. |
| C2 — dependency | Adjacent subsystem or document needed to resolve a concrete dependency; record why. |
| C3 — exception | Whole-file, whole-authority or repository-wide inspection only when explicitly required or a scoped conflict cannot be resolved. |

Authority precedence is not a reading checklist. The contract must state task ID, objective, exact baseline and CI, risk, compressed invariants, exact references, allowed/forbidden scope, acceptance, tests and stop conditions. A missing decision goes back to Gate Owner; Codex does not reconstruct project history or invent domain behavior. Every PR should deliver one coherent vertical capability where practical.

## Gate Owner Session Rebaseline

The repository is long-term authority; chat history is working memory only. Rebaseline on a fresh Gate Owner session and after a PR merge, exact-main CI result, Product Gate close, ADR acceptance, or material blocker or scope change. Fetch live main; read the relevant current CODEX policy and compact task state; verify the exact CI for the claimed checkpoint; then read only the governing authority needed for the active task. Live repository state wins over a handoff, memory or prior chat.

Before directing work, output a short readiness record: live main SHA, CODEX blob SHA, current gate, active task, conflicts and next authorized action. Collapse historical gates to their certified checkpoint status; do not replay all prior task history by default.

## Verification tiers

| Tier | Gate |
| --- | --- |
| T0 | Focused checks during the edit loop. |
| T1 | Regression for the affected subsystem. |
| T2 | Candidate lint, type, build and security checks appropriate to scope. |
| T3 | Full local, real-stack or E2E for Product/Security/high-risk closeout or an explicit task requirement. |
| T4 | Exact-head PR CI and exact-main post-merge CI wherever already required. |

Do not rerun full suites for each edit. A green parent or earlier commit never certifies a changed HEAD, including a docs-only baseline. Skips are reported as skips, not passes.

## Review tiers

| Declared risk | Review before required CI |
| --- | --- |
| Low | Codex verification. |
| Medium | Codex verification; one independent reviewer only when materially useful and specified in the contract. |
| High / Product / Security | Frozen snapshot, two independent reviewers and Gate Owner; applicable E2E/CI. |

A reviewer is read-only and receives the exact HEAD, file/hash evidence and scoped authority. A changed reviewed file invalidates that review. Codex verifies findings; reviewer absence cannot be reported as PASS.

## Evidence, resume and closeout

Prefer machine-generated diff, hashes, test results and runtime evidence over narrative claims. On interruption, record a compact TASK_STATE with baseline, branch/HEAD, completed checks, blocker and next action; keep secrets out. A fresh session fetches and revalidates those SHAs and CI before resuming. Final Dev closeout stays near 800 tokens: scope, evidence, limitations, exact HEAD/PR/CI and gate readiness.

Stop for baseline mismatch, missing or conflicting authority, ambiguous security/tenant/audit/idempotency rules, unapproved architecture or scope expansion, or an unmet prerequisite. Permanent human-approval and domain-command gates remain intact. OS-G2 needs its own authorization.
