# VALORA AI Project Brief

**Status:** Coordination guide only — not domain/design authority  
**Audience:** ChatGPT Control Plane, OpenCode workers/reviewers, human owner  
**Purpose:** Minimize expensive-model context while preserving VALORA authority, safety, auditability, and task scope.

## 1. Authority boundary

This file does **not** create or override VALORA product, domain, security, UX, data, or workflow rules.

For authoritative behavior, follow the repository hierarchy beginning with:

1. `CODEX.md`
2. `ENGINEERING_GUARDRAILS.md`
3. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
4. `docs/VALORA_PROJECT_HANDOFF.md`
5. Feature contracts / accepted ADRs / task-specific approved design

If this coordination guide conflicts with any authority above, the authority wins. Stop and escalate if the conflict affects the task.

## 2. Product in one paragraph

VALORA is a valuation / asset-identity workbench for non-IT business users. The Workbench and database are the operational source of truth; Word/Excel are controlled input/output ports. Client-facing UX is Vietnamese-first and must follow the active repository design authority. Evidence, decisions, tenant boundaries, official mutations, human confirmation gates, and AI provenance must remain auditable and safe.

## 3. AI operating model

VALORA uses two separated planes:

### Control Plane — ChatGPT

Primary responsibilities:

- clarify owner intent;
- translate approved requirements into bounded tasks;
- identify exact authority references;
- classify task risk;
- resolve product / BA / UX / architecture ambiguity;
- decide RED-risk escalations;
- review only the compact result or exception unless raw evidence is required.

ChatGPT should **not** be the default implementation worker.

### Execution Plane — OpenCode

Primary responsibilities:

- inspect the live repository;
- locate existing implementation and tests;
- classify the gap;
- implement the smallest safe patch;
- run tests / lint / build / security gates;
- perform independent cross-review;
- produce `TASK_RESULT.md`-compatible output.

Default low-cost workers may include:

- **DeepSeek V4 Flash** — repo inspection, gap mapping, test work, focused review, low/medium-complexity implementation;
- **Muse Spark 1.2** — implementation, debugging, multi-file code changes, codebase-oriented repair;
- equivalent low-cost models may substitute when unavailable, but the result must record the actual worker/reviewer.

No model may self-approve a high-risk change.

## 4. Core execution loop

Every task should follow:

```text
Owner intent
  -> ChatGPT Task Packet
  -> OpenCode repository inspection
  -> gap classification
  -> smallest safe patch
  -> tests / gates
  -> different-model cross-review when practical
  -> compact Task Result
  -> ChatGPT only if RED, BLOCKED, deviated, or owner requests review
```

The normal path is deliberately exception-driven. A successful low-risk task should not require ChatGPT to read raw diffs, terminal logs, or whole documents.

## 5. Token-minimization objective

Use repository references instead of repeating context.

Preferred:

```text
Authority: docs/adr/0030-...md §4.2
Scope: backend/app/modules/excel_import/...
Acceptance: tests X/Y/Z pass
```

Avoid:

- copying full authority documents into prompts;
- pasting full terminal transcripts;
- returning full diffs when a file list + evidence summary is enough;
- re-explaining closed decisions in every task;
- sending whole conversation histories to OpenCode;
- asking ChatGPT to reread the full repository after every implementation.

The unit of coordination is the **Task Packet**, not the chat history.

## 6. Live-state rule

Repository status can change faster than handoff prose.

Before code work, OpenCode must:

1. fetch / inspect current `origin/main`;
2. record the observed baseline SHA;
3. compare it with the task baseline, if one is specified;
4. inspect recent relevant commits when the task depends on implementation status;
5. stop rather than infer authorization if canonical handoff text appears stale or contradictory.

Historical SHAs and audit prose are evidence, not evergreen truth.

## 7. Scope discipline

Each task must have:

- one Task ID;
- one primary goal;
- explicit in-scope paths or components;
- explicit out-of-scope items;
- exact authority references;
- acceptance criteria;
- test/gate expectations;
- stop/escalation conditions.

Do not add unrelated refactors, redesigns, dependencies, workflows, roles, approval layers, KSCL flows, or domain behavior unless the task and authority explicitly require them.

## 8. Data and model safety

Never send the following to public/free model contexts unless an approved security process explicitly permits it:

- production secrets or credentials;
- API keys / tokens;
- real customer files;
- client-identifying data;
- production database dumps;
- private evidence documents;
- confidential business data not required by the task.

Use anonymized fixtures and minimal excerpts. Repository rules against secrets and real client files remain binding.

## 9. Success metrics

The coordination system should drive toward:

- 100% of implementation tasks using a Task Packet;
- >90% of GREEN tasks completed without ChatGPT code review;
- most YELLOW tasks returning only a compact result summary to ChatGPT;
- 0 invented domain rules by workers;
- 0 silent scope expansion;
- 0 raw customer/secret leakage to low-cost model contexts;
- 0 merge claims without evidence;
- ChatGPT used mainly for decisions, not repetitive repository execution.

## 10. Companion files

- `docs/ai/AGENT_RULES.md` — compact worker/reviewer operating contract
- `docs/ai/CONTEXT_INDEX.md` — minimal-context navigation map
- `docs/ai/ROUTING_RULES.md` — risk/model routing and escalation
- `docs/ai/TASK_PACKET.md` — task handoff template
- `docs/ai/TASK_RESULT.md` — execution/review result template
