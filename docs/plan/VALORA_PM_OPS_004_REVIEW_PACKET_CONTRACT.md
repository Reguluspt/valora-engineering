# PM-OPS-004 independent review packet contract v2.0

**Task:** [#160](https://github.com/Reguluspt/valora-engineering/issues/160), parent [#158](https://github.com/Reguluspt/valora-engineering/issues/158). **Status:** candidate tooling contract; Gate Owner owns certification. **Baseline:** main `19700f5bae21a2f144aeb2af3886ca5f919c55e4`, CODEX blob `de7e47d224a4f90bc190c182638d6a55c17540e5`, exact-main CI #652 / run 37884889977 SUCCESS 5/5, predecessor #159 certified/closed. Reverify live before freeze.

Authority: [CODEX §§8.1,10.1–10.4](../../CODEX.md), [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md), [Protocol v2](VALORA_AGENT_OPERATING_PROTOCOL_V2.md), [Compact Task Contract](VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md), [Dev Handoff](../../.agents/skills/valora-dev-handoff/SKILL.md), [official handoff](https://github.com/Reguluspt/valora-engineering/issues/160#issuecomment-6075125248), and certified [metrics contract v1.0](VALORA_PM_OPS_004_METRICS_CONTRACT.md) for byte/packet provenance terminology only. No modification to #159 tooling or contract.

## Input and authority selection

[`scripts/valora_review_packet.py`](../../scripts/valora_review_packet.py) is a Python stdlib offline CLI. An explicitly selected reviewed inventory is the only source selection input; there is no discovery of credentials, transcripts or customer material. Input is strict UTF-8 JSON with duplicate keys and unknown fields rejected. `--inventory-sha256` pins the exact reviewed inventory file bytes; obtain that digest at the review/approval checkpoint and compare it before dispatch. Recomputing a digest of an unreviewed inventory does not approve it.

Inventory input is at most 2,000,000 bytes, read with a bounded limit plus one sentinel byte; oversize input blocks before JSON parsing or output creation. This metadata limit never truncates Git source or packet bytes. CLI syntax/choice errors also emit only constant error codes, without rejected argument values. Blob identity uses SHA-1 as a non-security Git identifier (`usedforsecurity=False`); the separate SHA-256 remains the raw source digest.

Required top-level fields:

| Field | Constraint |
| --- | --- |
| `schema_version` | Exactly `2.0` |
| `task_id` | `VALORA-TASK-` followed by 1–100 uppercase letters/digits/hyphens |
| `base_sha`, `head_sha` | Exact lowercase 40-character Git SHA-1 commit objects; base must be an ancestor of HEAD |
| `branch` | Exact checked-out branch name; detached/wrong branch blocks |
| `public_source_reviewed` | Exactly `true`, asserting prior human review of source selection/privacy |
| `sources` | Unique source rows described below; exactly the union of changed paths and declared authorities |
| `authorities` | Unique required authority path/tier/span rows described below |

A source row contains exactly `path`, `revision` (`head` or `base`), `blob_sha`, `sha256` (raw blob SHA-256), `bytes` (raw UTF-8 bytes), and `lines`. A source path appears once, even when both changed and governing. Case-insensitive collisions block for Windows portability. All unchanged authority sources are at candidate HEAD. All changed candidate text files are at HEAD, with deleted files instead pinned to BASE and included in full. Renames are deliberately expanded into deletion/addition; the manifest keeps Git change status. Modified/deleted prior content is also checked for unsupported/private bytes and Git mode, but modified prior content is not included: this packet supplies full candidate source and is not a replacement for a separately required patch/before-state review.

An authority row contains exactly `path`, `tier` (`C1` or `C2`), and `spans` (nonempty list of inclusive `[start,end]` line ranges). Ranges must exist in the exact declared source, be positive, ordered canonically and nonoverlapping. Both CODEX.md and ENGINEERING_GUARDRAILS.md are mandatory. Other task-required protocol/ADR/contracts and their binding spans must be supplied in the reviewed inventory; omitted declared sources, invalid spans or inconsistent hashes block even in FULL mode.

**Semantic authority completeness belongs to the reviewed input.** The builder proves exact coverage of every declared required span and every actual changed path. It cannot infer which ADR/business rule applies to an arbitrary task, authenticate the reviewer of an inventory, or prove that a plausible in-bounds span contains the correct governing clause. Gate Owner must review the inventory against the task contract before pinning its digest. A newly identified missing authority requires a newly reviewed inventory and rebuilt packets. `declared_authorities_complete` never claims independent semantic or Gate approval.

## Modes, source bytes and manifest

- `scoped`: full content of every changed file, plus all declared C1/C2 spans from unchanged authority sources. If an authority is also changed, its complete source includes all spans.
- `full`: full content of every changed file and every required authority source.
- `full --escalate CONTEXT_INSUFFICIENT`: explicit scoped-to-full escalation on the same reviewed inventory/HEAD, recorded in packet and manifest. When the authority source set itself changes, review and pin the new inventory first.

Git operations read explicitly pinned local commit/tree/blob objects using argument arrays, no shell or Git writes. Global/system Git config and inherited `GIT_*` overrides are excluded; replacement objects, lazy fetch, optional locks, external diff, text conversion, external attributes and fsmonitor are disabled. Repositories with local clean/smudge filter configuration block before status can execute a filter. Status ignores unrelated submodule internals; selected or changed submodule content always blocks by Git mode. No provider or GitHub calls. The CLI verifies exact branch/HEAD and clean status both before and after reading sources. Source/GitHub remains read-only; the sole writes are two explicitly chosen new outputs outside the source worktree and its Git directories.

Git blob identity is recomputed as SHA-1 of `blob <raw-byte-count>\0<raw-bytes>`. SHA-256/byte/line counts must match the reviewed inventory. Strict UTF-8, LF and CRLF are supported without normalization; a final unterminated line and an empty changed file retain exact identity. Mixed LF/CRLF, bare CR, BOM, binary/control bytes, malformed UTF-8, symlinks, submodules, unsafe/private paths and unsupported file extensions block. Only regular text blobs (100644/100755) are admitted. All source identities and declared spans are validated before any output creation.

Packet format starts with `VALORA REVIEW PACKET v2`, then a canonical ASCII JSON identity header. Each ordered source/span is framed by `BEGIN SEGMENT` plus its canonical metadata, exact source bytes, and `END SEGMENT <index>`; full files also have `COMPLETE FILE <path>`. Packet ends with `END PACKET`. Markers are navigation aids: source can contain marker-like text, so parsing/verification must use the manifest's byte offsets and lengths rather than delimiter search.

Manifest serialization is UTF-8 ASCII-compatible JSON, sorted keys, compact separators, one trailing LF. It records schema version, task/base/HEAD/mode/escalation, normalized inventory digest, actual changed paths/statuses, declared authorities, ordered complete source identities and segments, source offsets/line ranges, packet offsets, UTF-8 byte counts, SHA-256 digests, complete-file flags and final packet digest/byte count. Source `sha256` is the complete raw blob digest; segment `sha256` hashes exactly the transported bytes, which equal the raw source slice. `inventory_sha256` in the manifest hashes the canonical normalized inventory, allowing order-independent output; the CLI's exact input-file digest separately guards external inventory approval. Neither digest is a token estimate.

Both reviewers receive one byte-identical packet and its manifest on the same frozen HEAD. Byte offsets reconstruct every span directly from its Git blob. `verify` rereads current pinned Git sources, rebuilds the canonical manifest/packet and compares both byte-for-byte; changed/missing/truncated/tampered packet or manifest blocks. Reordering inventory source/authority/span entries does not change outputs. A different mode or explicit escalation changes packet identity and requires dispatch parity revalidation.

## Privacy, output and limits

Public/synthetic source review is mandatory before invocation. Conservative path/extension restrictions and obvious private-key/provider-token detection block common accidental exposure. They cannot detect arbitrary customer data, disguised credentials, private reasoning in an otherwise ordinary text file or deliberate obfuscation. The boolean is a source assertion, not an automatic sanitizer. Do not feed raw transcripts, native reasoning, credentials or real appraisal/customer data to the builder, including fixtures. Review reports are retained separately under existing process controls, never ingested as packet source.

Errors return constant codes on stderr without echoing rejected source, paths, values or exception text. Exit 0 means verified byte evidence only, with `gate_authority=NONE`; exit 2 means BLOCKED. Existing outputs are never overwritten; both outputs must differ from one another and the inventory. Validation failures create neither output. IO failures during exclusive creation can leave an incomplete output: discard it and rebuild at new destinations, then verify before dispatch. Untracked output files inside the worktree would conflict with clean-source claims, so they are prohibited.

Supported source extensions are the explicit text allowlist in the script. SHA-256-format Git repositories, non-ASCII/space-containing source paths, binary/Office/image content and unsupported extensions require a separately approved tool capability; they block here. The tool does not mutate PR/CI state, adjudicate findings, infer review PASS, estimate tokens, or claim savings/certification.

## CLI and validation

After reviewing `inventory.json` and retaining its digest, use new output paths outside the repository. The same commands work on Windows/Linux with Python 3.12+ and Git installed:

```text
python scripts/valora_review_packet.py build --repo REPOSITORY_ROOT --inventory inventory.json --inventory-sha256 REVIEWED_FILE_SHA256 --mode scoped --packet scoped.packet.txt --manifest scoped.manifest.json
python scripts/valora_review_packet.py verify --repo REPOSITORY_ROOT --inventory inventory.json --inventory-sha256 REVIEWED_FILE_SHA256 --packet scoped.packet.txt --manifest scoped.manifest.json
python scripts/valora_review_packet.py build --repo REPOSITORY_ROOT --inventory inventory.json --inventory-sha256 REVIEWED_FILE_SHA256 --mode full --escalate CONTEXT_INSUFFICIENT --packet full.packet.txt --manifest full.manifest.json
python -m unittest discover -s scripts/tests -p test_valora_review_packet.py -v
```

T0/T1 cover raw Git/hash/count/range identity, complete changed-file coverage, source reconstruction, deterministic ordering, full/scoped golden output, actual CLI/verify/parity, LF/CRLF/empty/final-line handling and integrity/privacy failures in synthetic temporary repositories. Golden packet JSON retains exact packet bytes as hex, avoiding mixed-newline text fixture transport; tests decode it and compare the executable output byte-for-byte. Golden manifests remain canonical JSON. Fixtures contain no real customer material.

T2 covers stdlib import boundary, compile/lint, static offline/privacy checks, references, bounded scope and whitespace. Product runtime/PostgreSQL/browser T3 is N/A for this offline tooling task; CLI integration under T1 is mandatory. Repository CI does not execute these new script tests; preserve local native test evidence separately. Required two independent native DeepSeek/Gemini read-only reviews, complete finish evidence/adjudication and exact frozen-HEAD CI 5/5 remain delivery gates. Leave PR Draft; Gate Owner owns Ready/merge and post-merge certification. #161–#163 and 004-06 remain outside this task.
