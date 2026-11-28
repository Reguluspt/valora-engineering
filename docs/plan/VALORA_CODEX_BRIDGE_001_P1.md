# VALORA-CODEX-BRIDGE-001 — P1 offline contract

Authority: [PM checkpoint 6144781514](https://github.com/Reguluspt/valora-engineering/issues/200#issuecomment-6144781514), Issue #200, live CODEX §§1/8.1/10 and Agent Operating Protocol v2. The PO explicitly requested P1 offline implementation in this chat. P2 stays blocked.

Baseline: `origin/main` at `b482c999d17a983af3ae99e16026e4261e862a27`; exact CI #662 / run 37962101954 completed SUCCESS. CODEX blob: `de7e47d224a4f90bc190c182638d6a55c17540e5`. Worktree: `worktrees/valora-codex-bridge-001-p1-offline`; branch: `codex/valora-codex-bridge-001-p1-offline`.

Execution model: inherited Codex GPT-6 session; harness reasoning effort is not exposed and is not invented. No provider/model routing or child inference. PM handoff omits its formal CODEX MODEL block; direct PO authorization covers this bounded offline work, and a corrected model/budget block is still required before P2. OpenViking is non-authoritative; automatic recall/capture/injection OFF, optional manual recall only after bootstrap, ≤300 normally/≤600 resume/≤1000 with justification. No registered OpenViking tools are available here.

Risk: Security tooling. Reach is one owner/private queue (observed); compromised collaborators or credentials are an estimated threat. Capability is authenticated Issue editing or replay; motive is local execution/token theft; potential blast radius is irreversible disclosure. Use one strict boundary and make real execution unreachable in P1. No paid calls, credential provisioning, admin changes, product/runtime/#199/PM-OPS/reviewer/CI/SOP/CODEX changes.

## Work and verification

1. Implement strict signed synthetic task envelope, author/authority mapping and fixed read-only intent → negative schema/spoof/edited-body/control-Issue tests.
2. Implement durable state/journal/outbox, serialized reservation and restart recovery → replay/concurrency/partial-failure/lease/kill tests.
3. Implement bounded pull transport and backoff with injected transport, fake executor and offline-only entrypoint → offline/401/429/304/public-queue/redaction tests. HTTP adapter remains uninvoked with live credentials.
4. Prepare Codex invocation manifest and user-mode runbook → CLI help/login checks and non-inference sandbox fixture if safe; record actual limits.
5. Review scoped diff and run stdlib tests/static/document checks → local evidence; scoped Draft PR if proposed, with required review/exact-head CI still separate from PM certification.

Allowed paths: `scripts/codex_bridge/**`, `scripts/tests/test_codex_bridge.py`, `docs/plan/VALORA_CODEX_BRIDGE_001_P1.md`, `docs/implementation/VALORA_CODEX_BRIDGE_001_P1.md`. New dependencies: none. Frontend authority: N/A. Domain ADR: N/A; private authorization provisioning requires PM agreement before live use.

## P1 boundary and authorization design

Private repository identity is pinned to `Reguluspt/valora-task-queue`, ID `1416927556`; control #1 never dispatches. A task is a standalone versioned JSON Issue body with an explicit action marker, not Markdown/comment/shell text. Verify REST author numeric ID/login and local issuer-to-intent/scope grants. A separate HMAC over the entire canonical task prevents Issue-body edits from borrowing an allowed author's identity. Synthetic tests use a publicly marked fixture key; it is never a live credential. Live signer/key provisioning and PM signing delivery are unresolved and therefore P2 blockers, not an invented operational service.

All P1 tasks require offline model policy (zero inference calls) and the sole `read_fixture_v1` intent. Local policy freezes repo/ref/SHA/workspace/machine and checks them immediately before fake execution. Schema forbids arbitrary commands/prompts/paths and unknown fields. One OS lock and SQLite unique receipts serialize this installation. CLAIMED/RUNNING after restart become BLOCKED permanently; uncertain effects are never retried. Each task has max attempts 1 and a bounded lease/deadline. Append-only events and pending evidence survive reconnect; publication retries do not rerun execution. Remote publication is at-least-once with exact result-body reconciliation, not a distributed exactly-once claim.

Local owner policy, state directory, executable and fixture directory must be protected from untrusted local edits. SQLite enforces append-only event behavior but is not tamper-proof against the Windows account owning the file. A second independently configured installation is outside the singleton guarantee; bootstrap permits one state root only.

Acceptance: runnable offline replay, deterministic security/recovery tests, bounded sanitized artifacts, bootstrap/kill/rollback instructions, explicit unresolved live gates. Code tests do not certify installation, host sandbox or P2. No Gate self-certification, Ready, merge, deploy or Issue closure.
