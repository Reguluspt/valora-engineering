---
name: valora-session-bootstrap
description: Use when starting or resuming a Valora Gate Owner, Architect or Dev/Codex session before task execution or optional memory recall.
---

# Session bootstrap

Follow the [current operating protocol](../../../docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md). For Dev/Codex, validate the handoff's populated `CODEX MODEL` block using the [handoff skill](../valora-dev-handoff/SKILL.md).

Use the [live-authority bootstrap](../valora-live-authority-bootstrap/SKILL.md) for live-state mechanics: fetch origin; verify main SHA, CODEX blob, exact-main CI's head/completion/SUCCESS, assigned task branch/HEAD/worktree and current Issue/PR/gate. Verify any separate execution baseline and exact CI against the contract. Inspect status/diff read-only before editing. Memory/chat cannot certify SHA, CI, PR, Issue, changed files or worktree state. Stop on baseline drift, missing prerequisite or authority conflict.

Read relevant verified CODEX sections (normally §1, §8.1, §10 and task-relevant gates), then named task authority. Full CODEX/history reads need explicit scope or a concrete conflict and justification. Establish the compact [VALORA_LEAN_MCP policy](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md#mcp-usage-block): non-authoritative; bootstrap first; recall optional; normal ≤300 / resume-debug ≤600 / exceptional ≤1000 justified before retrieval; automatic recall/capture/injection OFF; no secrets/client data or volatile-state persistence; outage falls back to the protocol. A full profile read is needed only for MCP use/debug/persistence.

Output `PROJECT AUTHORITY READY: YES/NO` with live main, CODEX blob, exact-main CI, current gate, active task/Issue/PR, branch/worktree, conflicts and next authorized action. Gate Owner then derives the compact contract; Codex validates its task delta, named authority, scope and evidence requirements, loads the relevant task-specific skill, optionally recalls useful context, then executes. Readiness grants no later product or integration gate.
