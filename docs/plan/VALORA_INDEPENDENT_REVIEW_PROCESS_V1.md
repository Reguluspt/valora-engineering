# VALORA Independent Review Procedure v1.0 — Codex → AGY / OpenCode → PM

**Effective PO decision:** 20/11/2026. **Class:** process/documentation only. **Authority:** live PO instruction > [CODEX.md §10.1](../../CODEX.md#101-responsibilities) > permanent [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md) > accepted scoped contract. [Issue #254 PO review-tool delegation](https://github.com/Reguluspt/valora-engineering/issues/254#issuecomment-7041377013) applies to **technical design advice**; [Issue #221](https://github.com/Reguluspt/valora-engineering/issues/221) governs formal PR Independent Review. Do not infer a production implementation or merge authorization from this process.

## 1. Two review lanes — NEVER silently substitute one for the other

| | Lane D — Independent Design Advisory | Lane P — Formal Independent PR/Candidate Review |
| --- | --- | --- |
| Purpose | Critique architecture, security, domain design, readiness and source-scope gaps *before* coding | Assess implementation candidate and product/security gate evidence *after* frozen candidate exists |
| Dispatch owner | **Codex** sends reviewer prompt directly and waits for one native final | **Codex** dispatches Reviewer A/B directly, separate clean sessions, same exact frozen HEAD |
| Reviewer | AGY or OpenCode, one or both when PO/task asks | A: OpenCode `opencode-go/deepseek-v4.1-flash`; B: AGY `gemini-3.8-flash-high`, subject to actual availability and current CODEX/PO route |
| Tools | Reviewer chooses available code inspection, search, shell, web/MCP and other **investigative** tools; do not impose default VM/C1–C8/long preflight ladders on a simple advisory | Reviewer chooses own inspection tools inside the **technically verified read-only candidate boundary** required by CODEX §10.1/#221/task |
| Scope and output | Frozen design/Contract, code main vs local candidate clearly distinguished; `ACCEPTABLE_DESIGN / NEEDS_CHANGES / INCOMPLETE`; technical recommendations | One frozen candidate and CI; `PASS / FAIL / INCOMPLETE`; required A/B by risk, exact same HEAD and sealed candidate evidence |
| What this proves | **Advice**, not Security Owner/Domain Owner signed acceptance or implementation authorization | Reviewer assessment of candidate only; CI/T0–T3/PM/PO certification and named Owner approvals remain separate |

**Priority:** Lane D tool freedom means reviewers can *inspect/research with tools*, **not** self-authorize modification of VALORA source/test/CI, Git pushes, credentials, customer data, live APIs/DB, cloud accounts or deployment. Use authorized nonsensitive inputs. Known ambient MCP/web capability is disclosed; it is **not** silently marked security-isolation PASS. Real provider/platform policy failures or an actual unauthorized side effect require STOP and PM notice, not a fabricated review result.

## 2. Simple Codex-to-reviewer flow (both lanes)

1. **Identify lane, reviewer and authority** in one Compact Task Contract: purpose, exact main and (where applicable) candidate HEAD, approved Contract/design sources, 36/7 or other scope, no-implementation boundaries, model/effort. For Lane D, original source can be read-only evidence on the task's current baseline; do not falsely call a future 36-path source implementation.
2. **Private Space documents MUST travel PO-mediated, not as links.** If the canonical Contract/packet is stored in a private ChatGPT Space, **PM/Gate Owner reads it under their authorized access, exports an actual read-only file packet (e.g. Markdown ZIP with SHA256SUMS + source manifest), hands the packet to PO in the conversation, and PO explicitly transfers it to Codex/reviewer using their approved attachment/file channel**. Do not tell Codex to open private `chatgpt.com/space/page_...` URLs or to bypass sign-in; links are provenance for PO, **not** received reviewer evidence. Codex first verifies the actual transferred files and checksums, then verifies pinned `main` vs local candidate/previous tests. If PO transfer has not occurred, record `SOURCE_PACKET_NOT_DELIVERED` and STOP; do not relaunch a doomed link-only reviewer.
3. **Dispatch exactly one short whole-review prompt per requested reviewer** via its actual installed CLI/agent **only after PO confirms file transfer and Codex validates the source archive**, rather than using inaccessible Space links. Reviewer decides its own read/search/analysis paths. Do **not** force staged W1–W5 choreography, tool-call counts, custom monitoring, default C1–C8/VM/MCP feasibility jobs or automatic retries for Lane D. For Lane P keep mandatory CODEX §10.1 technical read-only boundary; no advisory simplification waives it.
4. **Wait for the genuine native final.** A CLI exit 0 or model tool count is *execution status*, never a positive design/security verdict. If missing/partial/403, mark `INCOMPLETE`. Do not silently swap models, send peer review findings into a supposedly blind first opinion, or let reviewer change app code.
5. **Codex as courier:** retain original unedited complete reviewer response (or immutable exact reference and hash), role/provider/model/effort, real baseline/candidate SHA, known tool summary, limitations, invocation status and before/after source integrity evidence proportionate to task. Deliver raw report **to PM** with a brief factual receipt, not Codex's unilateral acceptance decision.
6. **PM/Gate Owner owns substantive adjudication:** read original report, independently verify material file:line claims and test provenance, classify `VALID / INVALID / DUPLICATE / OUT_OF_SCOPE / ADVISORY / UNVERIFIED`, prioritize severity, identify design/scope decisions and present options to PO. Never call expected unimplemented requirements on a blocked future stage an actual released regression. Name any missing actual Security/Domain human signoff separately.
7. **Only after explicit PO/PM authorization**: adjust Contract/allowlist/DoR, perform implementation via Codex and T0–T3, then formal Lane P A/B on a fresh frozen candidate and exact-SHA CI/merge gates as required. A new candidate invalidates old formal reviews.


### Mandatory private-source receipt for VALORA #254 and future reviews

PM provides a **source-export artifact** to the PO before issuing an executable review prompt. The artifact must contain the required canonical Contract, Security/Domain packets, exact approved scope when applicable, and a neutral task authority; each extracted Space Page must retain its title/page ID, snapshot/extraction method and file SHA-256. The archive has a README and hash manifest, and does **not** contain previous AGY/OpenCode reviews or PM adjudication when the new review is intended to be blind. The PO, **not Codex**, transfers this actual artifact to Codex. Codex records receipt, validates per-file checksums and names every file read. PM remains responsible for deciding whether sources are sufficient for a reviewer verdict. Private Space page links may be retained only as provenance for the authorized PO.

## 3. Reviewer-specific routing

### AGY / Gemini (design advisor, or formal Reviewer B when Lane P)

- Codex invokes AGY itself using the **actual available** `gemini-3.8-flash-high` HIGH review route or a separately PO-approved successor; do not guess installed aliases. AGY may use installed **investigative** tools for Lane D and reports tools used when available.
- Legacy AGY 1.5.3/1.5.9/1.5.11 binary-specific canary/VM decisions belong to historical controlled Lane P or explicitly tasked security tests. They are **not an automatic new pre-review task for Lane D** after PO's 20/11 simplification.
- Any external-capable MCP server is still a source-disclosure consideration: provide only source explicitly authorized for the provider/tools, no credentials, personal/client data or protected runtime databases.

### OpenCode (design advisor, or formal Reviewer A when Lane P)

- Codex invokes installed `opencode` with the project-authorized model `opencode-go/deepseek-v4.1-flash` when available; use a clean independent session and a source/Contract packet comparable to AGY's. Do not assume that a report from AGY implies an OpenCode report exists.
- The current official OpenCode [permissions](https://opencode.ai/docs/permissions) describe **V2** `permissions` rules for `read`, `edit`, `shell`, `webfetch`, `websearch`, `external_directory`, MCP tool actions and more, with `allow/ask/deny` outcomes; older versions may instead use `permission`/`bash`. Inspect the installed CLI/version before supplying flags or config examples. **Do not change global user settings** just to make review run. Scope researcher tools to the approved material and distinguish ordinary inspection from mutations/externally side-effecting actions.
- For Lane P, keep formal read-only candidate integrity and independent same-HEAD A/B rules, regardless of tool availability in Lane D.

## 4. Minimal native report contract

```text
REVIEW LANE: D | P
REVIEWER: AGY | OpenCode
ACTUAL MODEL / EFFORT / STATUS / INVOCATIONS:
SOURCE: exact main SHA; candidate HEAD if present; canonical Contract access or missing refs
VERDICT: ACCEPTABLE_DESIGN | NEEDS_CHANGES | INCOMPLETE (D)
         PASS | FAIL | INCOMPLETE (P)
FINDINGS: ID | severity | file:line/source | evidence | effect | proposed action
SCOPE: exact added/forbidden path needs (MANDATORY / OPTIONAL / UNPROVEN)
TESTS: actual performed vs historical vs proposed; do not merge these
LIMITATIONS: unreadable contract / absent runtime evidence / no independent signoff
RAW NATIVE FINAL: full original + hash/reference
```

Codex returns this factual receipt plus the unedited native final. PM's disposition is a **separate** artifact; don't silently rewrite reviewer verdicts. For high-risk Lane P, complete actual A/B + test/CI/Gate and do not certify `PASS` from design advice.

## 5. VALORA S1 #254 example (20/11/2026)

- AGY completed **one Lane D advisory**: `gemini-3.8-flash-high`, effort HIGH, native final received; reviewer reports **4 Critical / 3 High / 3 Medium / 1 Low**, conclusion `REJECTED FOR IMPLEMENTATION`. These are reviewer classifications, **not automatically PM-validated independent owner acceptance**.
- PM checked main evidence: `AnalysisDraft` drops staging UUID; `load()` overwrites drafts; App `hashchange` unmount risks historic `FAIL_PRICE_LOST`; `/auth/me` lacks incarnation. Current 36-path scope is **conditional/inactive**. AGY's claimed mandatory 37th file `frontend/src/api/client.ts` requires independent necessity proof by Security Owner/PM and explicit PO scope decision; backend mapping service should not be opened just because suggested.
- Native report's local file links and 403 on canonical Space pages must remain labeled limitations. No AGY review proves original T3 rerun; do not claim implementation is already written. `SEC_A`, `DOM_A`, `DOR` still NOT_VERIFIED; `PRECHECK_RELEASE=ABSENT`; `S1_STAGE1=BLOCKED`.

This procedure changes **review orchestration only**. It is not a CI, security, access, app state, data, implementation or merge waiver.
