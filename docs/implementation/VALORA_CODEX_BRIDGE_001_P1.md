# VALORA-CODEX-BRIDGE-001 — P1 offline evidence and Windows runbook

Recorded: 2026-10-13, Asia/Saigon. **P1 local implementation/test evidence; not PM certification. P2 NOT RUN.** [Scoped contract](../plan/VALORA_CODEX_BRIDGE_001_P1.md) and [PM checkpoint](https://github.com/Reguluspt/valora-engineering/issues/200#issuecomment-6144781514) govern this package. Runtime stays SUPPLIER_QUOTES.

## Delivered boundary

The standalone Python stdlib package under `scripts/codex_bridge` validates private Issue envelopes and drives a serialized fake executor. It includes a dormant bounded GitHub REST adapter, durable SQLite receipts/events/result outbox, 60-second poll/backoff logic and STOP handling. Its runnable entrypoint has no live mode, no credential discovery and no Codex launcher. It cannot dispatch the private control Issue #1. Existing public comments, labels, titles and repository instructions never become executable task text.

GitHub author ID/login must match local issuer policy. The action marker, authority, intent and scope must match the local fixed grant. A separate HMAC authenticates all task fields, so a collaborator editing an owner's Issue body cannot borrow that owner's authorization. P1 uses only an explicitly public synthetic fixture key. Live signer provisioning/PM signing delivery remains unresolved; no signer credential was created or exported. This is a conservative offline design decision for PM review before P2.

Claims and append-only audit events commit together before execution; unique task/nonce/idempotency/Issue receipts survive restart. The OS file lock plus durable active-claim check caps this installation at one active task. On restart, unfinished CLAIMED/RUNNING records become BLOCKED even before lease expiry; the bridge never guesses that an uncertain task is safe to repeat. Only result publication retries, with reconciliation against an exact comment body from the configured result author. This is local at-most-once launch policy and remote at-least-once evidence publication, not distributed exactly-once execution.

SQLite events reject UPDATE/DELETE. Default limits are 10,000 events and 16 MiB for database growth checks; capacity exhaustion stops dispatch. There is no destructive rotation or receipt deletion. Local state is not tamper-proof against its owner. No Valora database schema, migrations or production job queue are involved.

## Versioned Issue body

Canonical JSON is the entire Issue body. Maximum 8192 UTF-8 bytes; reject duplicate keys, NaN/Infinity, excessive nesting, unknown/missing fields, wrong types and Markdown wrappers. `schema.py` is the executable schema source; `offline.fixture_issue` constructs a complete synthetic envelope.

| Field | P1 requirement |
| --- | --- |
| `schema_version`, `action` | Integer 1; `VALORA_CODEX_TASK_V1` |
| `task_id`, `nonce`, `idempotency_key` | Distinct durable receipt roles; 16–64 ASCII letters/digits/underscore/hyphen |
| `issuer`, `authority` | Numeric REST author ID `130158621`; `PO_SYNTHETIC_READ_ONLY`; login pinned separately to `Reguluspt` |
| `intent`, `approved_scope` | `read_fixture_v1`; exactly `["fixture:read"]` |
| `target_repo`, `target_ref`, `required_base_sha` | Frozen local target/ref; exact 40-character lowercase Git SHA matching policy and fresh head provider before launch |
| `workspace_id`, `machine_id`, `agent_id` | Exact local policy identifiers; no Issue-supplied filesystem path |
| `created_at`, `expires_at` | UTC `YYYY-MM-DDTHH:MM:SSZ`; no future creation, expiry still ahead, TTL ≤3600 seconds |
| `max_attempts`, `lease_seconds` | Exactly 1 attempt; integer lease 1–60 seconds; start cannot extend reservation deadline |
| `cost_policy` | Exactly `{mode: offline, model: none, max_inference_calls: 0}` |
| `acceptance_checks` | Exactly `["fixture_sha256"]` |
| `signature` | Lowercase HMAC-SHA256 of canonical sorted compact ASCII JSON excluding `signature`; independent issuer key ≥32 bytes |

Queue repo is pinned to `Reguluspt/valora-task-queue`, numeric ID `1416927556`, `private=true`; authoritative Issue URL/number/id/state must match and pull requests are rejected. Task validation and repo/head/current Issue checks repeat after reservation. Only the fixed `fixture.txt` name is readable by the fake executor, its content is pinned, and symbolic links/path escape are rejected.

The polling adapter uses the queue's repository Issues endpoint and refetches each Issue; it never reads comments as instructions. It limits response bodies to 1 MiB, pages to 10 ×100 and HTTP timeout to 10 seconds. Conditional GET is used only when page-one ETag covers the complete list. Redirects/proxies to other hosts are disabled. 401/404/non-rate-limit 403 require explicit operator restart; primary/secondary rate limits and Retry-After use bounded exponential scheduling. STOP is checked at one-second intervals during foreground waits.

[GitHub Issues REST documentation](https://docs.github.com/en/rest/issues/issues) specifies Issues permissions for this transport. Repo metadata and Issues reads/writes suffice for the proposed endpoint set; there is no Contents/PR/workflow/admin API requirement. Live PAT scope is not demonstrated by successful metadata reads and still requires owner's token-selection verification.

## Reproduce offline evidence

From a normal PowerShell terminal at the worktree root, using existing Python 3.12:

```powershell
py -3.12 -m unittest discover -s scripts/tests -p test_codex_bridge.py -v
py -3.12 -m compileall -q scripts/codex_bridge scripts/tests/test_codex_bridge.py
git diff --check
```

Run the synthetic foreground replay from `scripts`; keep state outside the checkout:

```powershell
$bridgeState = Join-Path $env:LOCALAPPDATA 'Valora/CodexBridgeOffline/state'
Push-Location scripts
py -3.12 -m codex_bridge --state-dir $bridgeState
py -3.12 -m codex_bridge --state-dir $bridgeState
Pop-Location
```

First run: one fake executor call, verified fixture hash, zero live queue calls and zero inference calls. Second run with the same state: zero executor calls and no duplicate execution. These timestamps/SHA are synthetic fixture pins, not live task evidence. Do not delete receipts to force replay; a new operator-approved synthetic task needs a new ID/nonce/receipt. The CLI fixture is intentionally fixed.

## Windows user-mode bootstrap — before any live gate

No administrator installation, new service, self-hosted Actions runner or paid API dependency is needed for offline tests. Do not schedule a live bridge: P1 contains no live dispatch entrypoint. Manual bootstrap remains unavoidable; automatic future task forwarding has not been demonstrated.

1. Keep one dedicated state directory and one bridge instance per host. Use a normal Windows account and a disposable fixture/worktree; keep local policy, executable and state unwritable by untrusted users. Do not run from the business-test environment.
2. PO creates a separate expiring fine-grained PAT in GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens. Resource owner `Reguluspt`; selected repository **only** `valora-task-queue`; repository Issues read/write and Metadata read. No account/admin/Actions/Contents/PR/workflow/secrets grants. Do not export the PM GitHub App credential or reuse the broad existing `gh` login for the bridge.
3. Store the PAT using Windows Credential Manager or a current-user DPAPI-protected file. Never paste it into ChatGPT, Issues, commits, screenshots or logs. The following optional manual preparation protects a dedicated local directory and encrypts a SecureString; it is a future owner step and was **not executed** in this task:

```powershell
$bridgeHome = Join-Path $env:LOCALAPPDATA 'Valora/CodexBridge'
New-Item -ItemType Directory -Path $bridgeHome -Force | Out-Null
$bridgeSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$bridgeAcl = Get-Acl -LiteralPath $bridgeHome
$bridgeAcl.SetAccessRuleProtection($true, $false)
$bridgeRule = [System.Security.AccessControl.FileSystemAccessRule]::new(
    $bridgeSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$bridgeAcl.SetAccessRule($bridgeRule)
Set-Acl -LiteralPath $bridgeHome -AclObject $bridgeAcl
$bridgeSecret = Read-Host 'Queue-only fine-grained PAT (local input only)' -AsSecureString
$bridgeEncrypted = ConvertFrom-SecureString -SecureString $bridgeSecret
Set-Content -LiteralPath (Join-Path $bridgeHome 'queue-pat.dpapi') -Value $bridgeEncrypted
Remove-Variable bridgeSecret, bridgeEncrypted
```

4. PM must approve the independent signer/key distribution mechanism and numeric issuer/result-author mapping. Do not use the public fixture key for live authorization. P1 does not load the DPAPI file; a reviewed live credential adapter and child-environment boundary are prerequisites for P2.
5. Before a new live capability, reverify the exact code/workspace SHA, CLI version/login, effective sandbox, model entitlement/remaining quota/overage controls, one-task/one-attempt ceiling and process-tree cancellation. Keep the PAT/signer key outside the Codex child environment. A protected file remains sensitive: read-only filesystem access alone is not credential isolation.

## Actual Windows sandbox fixture observation

Installed CLI: `codex-cli 0.162.0-alpha.17.2`; login status reports ChatGPT. No login, model call, token creation, system configuration or sandbox installation was performed. A **non-inference** `codex sandbox` probe ran a local Python canary using explicit MXC and `:read-only`:

```powershell
codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :read-only -C $bridgeProbe -- $pythonBinary probe.py
```

Observed stdout: `{"fixture_read": true, "write_denied": true}`; exit **0**. The probe reads a harmless fixture and tries to create a harmless file in its temporary directory; it passed on this Windows host. This is evidence for that command/profile only. It does not prove `codex exec` inference isolation, denied reads of credential locations, network restrictions, child-process cleanup or model budget. The disabled invocation manifest selects `--sandbox read-only`, explicit MXC, `--ignore-user-config`, `--json`, `--ephemeral`, fixed working directory and fixed prompt; no arbitrary full-access/bypass flags. Approval policy `never` denies elevation requests while sandbox restrictions remain in force.

[Official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode) and [Windows sandbox documentation](https://learn.chatgpt.com/docs/windows/windows-sandbox) describe those capabilities; actual installed help and the canary probe are the local evidence. Current interactive chat has full filesystem access and is not itself P2 sandbox proof.

## Kill switch, rollback and retained holds

Create an empty `STOP` file in the protected state directory to inhibit claims/launches, pause publication and end waits; Ctrl+C stops the foreground offline replay. A completed fake task observed during STOP is CANCELLED; uncertain unfinished records block permanently on restart. Fake execution is synchronous and cooperative; enforcement against a hung real child/process tree is **not implemented or certified** and remains required before P2.

Rollback: stop the foreground process, keep STOP in place, revoke the future queue PAT if provisioned, remove any future startup registration, and preserve the journal/outbox. This task installed no startup registration. Do not delete/rewrite receipts or audit events to make uncertain work rerunnable. Uninstalling this isolated code never changes Valora runtime or product data.

## Verification and remaining gates

Local suite: **47 tests, 47 passed, 0 failures, 0 skips** after corrections. Cases cover author/label/body/comment spoofing, signatures, schema/types/limits, control #1, scope/model denial, expiry/SHA drift, duplicate receipts, reboot before/after launch, lease hold, separate-process Windows locking, offline/reconnect, revoked credentials, rate limits/ETags/pagination, partial POST reconciliation, secret-shaped payload/output/exception redaction, capacity, append-only events, STOP and monotonic deadlines. The first suite run caught one Windows lock failure; it was fixed rather than skipped. A later Ruff check caught an assigned lambda; it was corrected.

CLI smoke: first replay 1 fake call / 0 live queue / 0 inference; second replay 0 fake calls. Sandbox canary: read allowed / write denied / exit 0. Compilation, scoped Ruff, document references and committed whitespace are checked before first push. No existing runtime/reviewer suite, business-test stack or provider inference was run or modified; live T3/P2 is out of scope.

Raw local artifacts live in `%TEMP%/valora-codex-bridge-001-p1/`: `unit-tests.log`, `sandbox-probe.log`, `offline-replay-first.json`, `offline-replay-second.json`. Tests reproduce the suite; CLI and probe examples reproduce bounded observations in fresh temporary state. Artifact hashes are reported in the local closeout record; do not confuse synthetic successful results with installed-host task processing.

Baseline CI #662 / run 37962101954 is SUCCESS on `b482c999d17a983af3ae99e16026e4261e862a27`; its 5/5 success is baseline evidence only. Candidate exact-head CI and two independent Security reviewers/PM gate remain separate. No automatic Ready, merge, deployment, Issue closure or P1/P2 certification.

Remaining owner/PM decisions: queue-only PAT and protected local handling; live signing/auth mapping; reviewed credential loader/environment separation; updated CODEX MODEL/compact live contract; approved Codex model/usage ceiling; effective inference sandbox including credential/network isolation; real process timeout/kill-tree proof; independent review/exact-head CI and explicit bounded P2 approval. Scope respected; no product ADR introduced, no new dependency or production migration.
