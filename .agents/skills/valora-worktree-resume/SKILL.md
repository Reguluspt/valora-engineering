---
name: valora-worktree-resume
description: Resume an interrupted or dirty Valora worktree with read-only inspection, live authority verification and a reviewed checkpoint.
---

# Worktree resume

Inspect read-only first: pwd/Get-Location, branch, HEAD, status, diff and diff/stat. Identify worktree ownership and distinguish valid task work from unrelated changes without staging or altering anything.

Then fetch origin and verify live CODEX, task authority and exact CI BEFORE checkpointing. Memory may suggest a procedure only after bootstrap; it cannot reconstruct HEAD, changed files, status or task state.

Review the exact diff and form an explicit file allowlist. Stage only those reviewed paths. NEVER use `git add .` or `git add -A`. Checkpoint valid work before reconciling with live main, within current commit authorization; if checkpoint authorization is absent, preserve the work and report that boundary. Reconcile safely and rerun required gates for the resulting HEAD.

Never use `reset --hard`, `git clean`, or delete/recreate a worktree unless separately explicitly authorized. Never modify another task's worktree. A stale handoff cannot authorize destructive recovery.

Follow the [profile](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md) and current CODEX; OpenViking outage falls back to Lean.
