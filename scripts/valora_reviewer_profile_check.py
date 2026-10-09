"""Offline sanitized reviewer-receipt preflight; never a review or Gate PASS."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

VERSION = "1.0"
MAX_BYTES = 2_000_000
MAX_ROWS = 1000
MODELS = {"deepseek": "opencode-go/deepseek-v4.1-flash", "google": "gemini-3.1-pro-high"}
SECTIONS = {"identity", "scope", "coverage", "findings", "negative_checks", "limitations", "conclusion"}
AXES = {"source_integrity", "authority", "correctness", "security", "tenant_rbac", "privacy", "audit",
        "cas_currentness", "tests", "review_completeness", "independence", "budget_telemetry"}
NA_AXES = {"tenant_rbac", "audit", "cas_currentness"}
SEVERITIES = {"P0", "P1", "P2"}
PUBLIC_REF = r"https://github\.com/Reguluspt/valora-engineering/(?:issues|pull)/[1-9][0-9]*#issuecomment-[1-9][0-9]*"


class Invalid(ValueError):
    """Only constant error codes may reach the CLI."""


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Invalid("INVALID_ARGUMENTS")


def require(condition, code="INVALID_SCHEMA"):
    if not condition:
        raise Invalid(code)


def shape(value, fields):
    require(type(value) is dict and set(value) == set(fields.split()))


def match(value, pattern):
    require(type(value) is str and re.fullmatch(pattern, value) is not None)


def digest(value, length=64, nullable=False):
    if value is None and nullable:
        return
    match(value, rf"[0-9a-f]{{{length}}}")


def integer(value, minimum=1):
    require(type(value) is int and minimum <= value <= 10**9)


def choice(value, allowed):
    require(type(value) is str and value in allowed)


def source_ref(value):
    require(value == "SYNTHETIC" or type(value) is str and re.fullmatch(PUBLIC_REF, value) is not None)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def safe_path(value):
    match(value, r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
    for part in value.split("/"):
        lower = part.lower()
        require(part not in {".", ".."} and not part.endswith("."), "UNSAFE_PATH")
        require(not re.fullmatch(r"(?:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", lower), "UNSAFE_PATH")
        require(lower not in {".git", ".ssh", ".aws", "private", "secrets", "credentials", "transcripts",
                              "client-data", "customer-data"} and not lower.startswith(".env"), "UNSAFE_PATH")
        require(not re.match(r"(?:auth|credentials|secrets)(?:\.|$)", lower), "UNSAFE_PATH")
    require(Path(value).suffix.lower() in {".py", ".md", ".json", ".txt", ".ts", ".tsx", ".js",
                                          ".yaml", ".yml", ".toml", ".rs", ".sql", ".ps1", ".css"}, "UNSAFE_PATH")


def rows(value, key):
    require(type(value) is list and len(value) <= MAX_ROWS)
    seen = set()
    for row in value:
        require(type(row) is dict and key in row)
        name = row[key]
        require(type(name) is str and name.lower() not in seen)
        seen.add(name.lower())
    return value


def files(value, authority=False):
    for row in rows(value, "path"):
        shape(row, "path blob_sha sha256 lines tier spans" if authority else "path blob_sha sha256 lines revision")
        safe_path(row["path"])
        digest(row["blob_sha"], 40)
        digest(row["sha256"])
        integer(row["lines"], 0)
        if authority:
            choice(row["tier"], {"C1", "C2"})
            require(type(row["spans"]) is list and 0 < len(row["spans"]) <= MAX_ROWS)
            previous = 0
            for span in row["spans"]:
                require(type(span) is list and len(span) == 2)
                integer(span[0])
                integer(span[1])
                require(previous < span[0] <= span[1] <= row["lines"])
                previous = span[1]
        else:
            choice(row["revision"], {"base", "head"})


def identity(value):
    shape(value, "task_id base_sha head_sha packet_sha256 packet_bytes inventory_sha256")
    match(value["task_id"], r"VALORA-TASK-[A-Z0-9-]{1,100}")
    digest(value["base_sha"], 40)
    digest(value["head_sha"], 40)
    digest(value["packet_sha256"])
    digest(value["inventory_sha256"])
    integer(value["packet_bytes"])


def report(value):
    if value is None:
        return
    shape(value, "state sha256 source sections changed_files authorities coverage severity_checks findings")
    choice(value["state"], {"COMPLETE", "INCOMPLETE", "UNKNOWN"})
    digest(value["sha256"], nullable=True)
    source_ref(value["source"])
    for section in rows(value["sections"], "section"):
        shape(section, "section evidence_sha256")
        choice(section["section"], SECTIONS)
        digest(section["evidence_sha256"], nullable=True)
    files(value["changed_files"])
    files(value["authorities"], authority=True)
    for axis in rows(value["coverage"], "axis"):
        shape(axis, "axis state rationale evidence_sha256")
        choice(axis["axis"], AXES)
        choice(axis["state"], {"REVIEWED", "N/A", "MISSING", "UNKNOWN"})
        require(axis["rationale"] is None or axis["rationale"] in {"NO_RUNTIME_CHANGE", "OFFLINE_ONLY"})
        digest(axis["evidence_sha256"], nullable=True)
    for check in rows(value["severity_checks"], "severity"):
        shape(check, "severity state evidence_sha256")
        choice(check["severity"], SEVERITIES)
        choice(check["state"], {"NONE", "FINDINGS", "MISSING", "UNKNOWN"})
        digest(check["evidence_sha256"], nullable=True)
    for finding in rows(value["findings"], "id"):
        shape(finding, "id severity path start end scenario_sha256 evidence_sha256 disposition")
        match(finding["id"], r"f-[0-9a-f]{8}")
        choice(finding["severity"], SEVERITIES)
        safe_path(finding["path"])
        integer(finding["start"])
        integer(finding["end"])
        require(finding["start"] <= finding["end"])
        digest(finding["scenario_sha256"])
        digest(finding["evidence_sha256"])
        choice(finding["disposition"], {"UNADJUDICATED", "VALID", "INVALID", "DUPLICATE", "OUT_OF_SCOPE", "ADVISORY"})


def attempt(value):
    shape(value, "id provider attempt session_sha256 identity model_requested model_native native independence report retry telemetry")
    match(value["id"], r"a-[0-9a-f]{8}")
    choice(value["provider"], set(MODELS))
    integer(value["attempt"])
    digest(value["session_sha256"], nullable=True)
    identity(value["identity"])
    choice(value["model_requested"], set(MODELS.values()))
    require(value["model_native"] is None or value["model_native"] in set(MODELS.values()))
    native = value["native"]
    shape(native, "terminal_status finish_reason terminal_evidence_sha256 finish_evidence_sha256 source")
    choice(native["terminal_status"], {"COMPLETED", "INCOMPLETE", "ERROR", "UNKNOWN"})
    choice(native["finish_reason"], {"stop", "STOP", "length", "MAX_TOKENS", "completed", "incomplete",
                                     "UNKNOWN", "NOT_EXPOSED", "error", "content_filter", "SAFETY", "tool_calls"})
    digest(native["terminal_evidence_sha256"], nullable=True)
    digest(native["finish_evidence_sha256"], nullable=True)
    source_ref(native["source"])
    independence = value["independence"]
    shape(independence, "isolated peer_reports_seen evidence_sha256")
    require(independence["isolated"] is None or type(independence["isolated"]) is bool)
    require(independence["peer_reports_seen"] is None or type(independence["peer_reports_seen"]) is bool)
    digest(independence["evidence_sha256"], nullable=True)
    if value["retry"] is not None:
        retry = value["retry"]
        shape(retry, "previous_attempt_id reason approval_ref settings_changed")
        match(retry["previous_attempt_id"], r"a-[0-9a-f]{8}")
        choice(retry["reason"], {"FINISH_LENGTH", "REPORT_INCOMPLETE", "MODEL_IDENTITY_CORRECTION",
                                 "CONTEXT_INSUFFICIENT", "TRANSPORT_FAILURE"})
        source_ref(retry["approval_ref"])
        require(type(retry["settings_changed"]) is bool)
    telemetry = value["telemetry"]
    shape(telemetry, "event_id snapshot_kind usage_format source")
    require(telemetry["event_id"] is None or type(telemetry["event_id"]) is str
            and re.fullmatch(r"e-[0-9a-f]{8}", telemetry["event_id"]) is not None)
    choice(telemetry["snapshot_kind"], {"per_turn", "cumulative", "delta", "UNKNOWN"})
    choice(telemetry["usage_format"], {"deepseek_chat", "gemini_generate", "runner_metadata", "UNKNOWN"})
    source_ref(telemetry["source"])
    report(value["report"])


def evaluate(value, expected):
    failures, unknown = set(), set()
    if value["identity"] != expected["identity"]:
        failures.add("STALE_SOURCE_OR_PACKET")
    model = MODELS[value["provider"]]
    if value["model_requested"] != model or value["model_native"] not in {None, model}:
        failures.add("MODEL_MISMATCH")
    if value["model_native"] is None:
        unknown.add("MODEL_IDENTITY_UNVERIFIED")
    native = value["native"]
    if native["terminal_status"] in {"INCOMPLETE", "ERROR"} or native["finish_reason"] in {
            "length", "MAX_TOKENS", "incomplete", "error", "content_filter", "SAFETY", "tool_calls"}:
        failures.add("NATIVE_ATTEMPT_INCOMPLETE")
    if native["terminal_status"] == "UNKNOWN" or native["terminal_evidence_sha256"] is None:
        unknown.add("TERMINAL_EVIDENCE_UNVERIFIED")
    if native["finish_reason"] == "NOT_EXPOSED" and value["provider"] == "google":
        if native["finish_evidence_sha256"] is not None:
            failures.add("FABRICATED_FINISH_EVIDENCE")
    elif native["finish_reason"] not in ({"stop"} if value["provider"] == "deepseek" else {"stop", "STOP"}) or native["finish_evidence_sha256"] is None:
        unknown.add("FINISH_EVIDENCE_UNVERIFIED")
    independent = value["independence"]
    if independent["isolated"] is False or independent["peer_reports_seen"] is True:
        failures.add("PEER_CONTAMINATION")
    if independent["isolated"] is None or independent["peer_reports_seen"] is None or independent["evidence_sha256"] is None or value["session_sha256"] is None:
        unknown.add("INDEPENDENCE_UNVERIFIED")
    final = value["report"]
    if final is None:
        failures.add("FINAL_REPORT_MISSING")
    else:
        if final["state"] != "COMPLETE" or final["sha256"] is None:
            failures.add("FINAL_REPORT_INCOMPLETE")
        if {x["section"] for x in final["sections"] if x["evidence_sha256"] is not None} != SECTIONS:
            failures.add("FINAL_SECTIONS_MISSING")
        for field in ("changed_files", "authorities"):
            if sorted(final[field], key=lambda x: x["path"]) != sorted(expected[field], key=lambda x: x["path"]):
                failures.add("SOURCE_COVERAGE_MISSING")
        if {x["axis"] for x in final["coverage"]} != AXES:
            failures.add("MANDATORY_AXIS_MISSING")
        for axis in final["coverage"]:
            if axis["evidence_sha256"] is None or axis["state"] in {"MISSING", "UNKNOWN"} or (
                    axis["state"] == "N/A" and (axis["axis"] not in NA_AXES or axis["rationale"] is None)):
                failures.add("MANDATORY_AXIS_MISSING")
        if {x["severity"] for x in final["severity_checks"]} != SEVERITIES:
            failures.add("SEVERITY_DISCUSSION_MISSING")
        for check in final["severity_checks"]:
            found = any(x["severity"] == check["severity"] for x in final["findings"])
            if check["evidence_sha256"] is None or check["state"] != ("FINDINGS" if found else "NONE"):
                failures.add("SEVERITY_DISCUSSION_MISSING")
        sources = {x["path"]: [[1, x["lines"]]] for x in expected["changed_files"]}
        for authority in expected["authorities"]:
            sources.setdefault(authority["path"], authority["spans"])
        for finding in final["findings"]:
            if not any(start <= finding["start"] <= finding["end"] <= end
                       for start, end in sources.get(finding["path"], [])):
                failures.add("FINDING_OUTSIDE_REVIEWED_SOURCE")
    return failures, unknown


def check(document, base, head, packet, inventory):
    shape(document, "schema_version profile_version sanitized_metadata expected attempts")
    require(document["schema_version"] == VERSION and document["profile_version"] == VERSION
            and document["sanitized_metadata"] is True, "SANITIZED_VERSION_REQUIRED")
    expected = document["expected"]
    shape(expected, "identity changed_files authorities")
    identity(expected["identity"])
    files(expected["changed_files"])
    files(expected["authorities"], authority=True)
    require(expected["changed_files"] and {"CODEX.md", "ENGINEERING_GUARDRAILS.md"} <= {
        x["path"] for x in expected["authorities"]}, "REVIEWED_INVENTORY_REQUIRED")
    changed = {x["path"].lower(): x for x in expected["changed_files"]}
    for authority in expected["authorities"]:
        other = changed.get(authority["path"].lower())
        if other:
            require(other["path"] == authority["path"] and other["revision"] == "head"
                    and all(other[k] == authority[k] for k in ("blob_sha", "sha256", "lines")), "INVENTORY_CONFLICT")
    for value, length in ((base, 40), (head, 40), (packet, 64), (inventory, 64)):
        digest(value, length)
    require((base, head, packet) == tuple(expected["identity"][k] for k in ("base_sha", "head_sha", "packet_sha256")), "EXPECTED_IDENTITY_MISMATCH")
    normalized = dict(expected, changed_files=sorted(expected["changed_files"], key=lambda x: x["path"]),
                      authorities=sorted(expected["authorities"], key=lambda x: x["path"]))
    require(hashlib.sha256(canonical(normalized)).hexdigest() == inventory, "EXPECTED_INVENTORY_MISMATCH")
    attempts = rows(document["attempts"], "id")
    results, latest = [], {}
    for value in attempts:
        attempt(value)
    for value in sorted(attempts, key=lambda x: (x["provider"], x["attempt"])):
        provider = value["provider"]
        prior = latest.get(provider)
        require(value["attempt"] == (prior["attempt"] + 1 if prior else 1), "ATTEMPT_HISTORY_INVALID")
        failures, unknown = evaluate(value, expected)
        if prior is None:
            require(value["retry"] is None, "ATTEMPT_HISTORY_INVALID")
        else:
            retry = value["retry"]
            if retry is None or retry["previous_attempt_id"] != prior["id"]:
                failures.add("RETRY_APPROVAL_MISSING")
            else:
                prior_failures, prior_unknown = evaluate(prior, expected)
                prior_codes = prior_failures | prior_unknown
                reasons = {
                    "FINISH_LENGTH": prior["native"]["finish_reason"] in {"length", "MAX_TOKENS"},
                    "REPORT_INCOMPLETE": bool(prior_failures & {
                        "FINAL_REPORT_MISSING", "FINAL_REPORT_INCOMPLETE", "FINAL_SECTIONS_MISSING",
                        "MANDATORY_AXIS_MISSING", "SEVERITY_DISCUSSION_MISSING"}),
                    "MODEL_IDENTITY_CORRECTION": bool(prior_codes & {"MODEL_MISMATCH", "MODEL_IDENTITY_UNVERIFIED"}),
                    "CONTEXT_INSUFFICIENT": "SOURCE_COVERAGE_MISSING" in prior_codes,
                    "TRANSPORT_FAILURE": prior["native"]["terminal_status"] in {"ERROR", "UNKNOWN"}
                        or "TERMINAL_EVIDENCE_UNVERIFIED" in prior_codes,
                }
                if not reasons[retry["reason"]]:
                    failures.add("RETRY_CLASSIFICATION_INVALID")
                if retry["settings_changed"]:
                    failures.add("UNVERIFIED_SETTINGS_CHANGE")
        latest[provider] = value
        state = "INCOMPLETE" if failures else "UNKNOWN" if unknown else "COMPLETE"
        results.append({"id": value["id"], "provider": provider, "attempt": value["attempt"],
                        "mechanical_preflight": state, "codes": sorted(failures | unknown),
                        "findings_count": len(value["report"]["findings"]) if value["report"] else 0})
    codes = set()
    current = [next(x for x in reversed(results) if x["provider"] == provider) for provider in latest]
    if set(latest) != set(MODELS):
        codes.add("REQUIRED_REVIEWER_MISSING")
    if any("STALE_SOURCE_OR_PACKET" in x["codes"] for x in results):
        codes.add("SOURCE_HISTORY_MIXED")
    if any(set(x["codes"]) & {"RETRY_APPROVAL_MISSING", "RETRY_CLASSIFICATION_INVALID", "UNVERIFIED_SETTINGS_CHANGE"}
           for x in results):
        codes.add("RETRY_HISTORY_INVALID")
    if len(latest) == 2 and latest["deepseek"]["session_sha256"] is not None and latest["deepseek"]["session_sha256"] == latest["google"]["session_sha256"]:
        codes.add("REVIEWER_SESSION_COLLISION")
    for provider, final_attempt in latest.items():
        history = [x for x in attempts if x["provider"] == provider and x["attempt"] < final_attempt["attempt"]]
        for previous in history:
            if final_attempt["session_sha256"] is not None and previous["session_sha256"] == final_attempt["session_sha256"]:
                if previous["independence"]["isolated"] is False or previous["independence"]["peer_reports_seen"] is True:
                    codes.add("CONTAMINATED_SESSION_REUSED")
                elif previous["independence"]["isolated"] is None or previous["independence"]["peer_reports_seen"] is None or previous["independence"]["evidence_sha256"] is None:
                    codes.add("SESSION_ISOLATION_HISTORY_UNVERIFIED")
            if previous["report"] and final_attempt["report"]:
                final_findings = {x["id"]: x for x in final_attempt["report"]["findings"]}
                for old in previous["report"]["findings"]:
                    new = final_findings.get(old["id"])
                    if new is None or new["severity"] > old["severity"] or any(
                            new[k] != old[k] for k in ("path", "start", "end", "scenario_sha256")):
                        codes.add("FINDING_HISTORY_LOST_OR_DOWNGRADED")
    state = "INCOMPLETE" if codes or any(x["mechanical_preflight"] == "INCOMPLETE" for x in current) else "UNKNOWN" if any(x["mechanical_preflight"] == "UNKNOWN" for x in current) else "COMPLETE"
    return {"schema_version": VERSION, "mechanical_preflight": state, "gate_authority": "NONE",
            "evidence_authenticity": "SOURCE_ASSERTED_NOT_AUTHENTICATED", "codes": sorted(codes), "attempts": results}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def read_document(path):
    require(path.suffix.lower() == ".json" and path.is_file() and not path.is_symlink(), "REGULAR_JSON_REQUIRED")
    with path.open("rb") as source:
        raw = source.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "INPUT_TOO_LARGE")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise Invalid("INVALID_JSON") from None


def reject_constant(value):
    raise Invalid("INVALID_JSON")


def main(argv=None):
    try:
        parser = SafeParser(description=__doc__)
        parser.add_argument("input", type=Path)
        parser.add_argument("--expected-base", required=True)
        parser.add_argument("--expected-head", required=True)
        parser.add_argument("--expected-packet", required=True)
        parser.add_argument("--expected-inventory", required=True, help="SHA256 of canonical reviewed expected metadata")
        args = parser.parse_args(argv)
        result = check(read_document(args.input), args.expected_base, args.expected_head,
                       args.expected_packet, args.expected_inventory)
        sys.stdout.write(canonical(result).decode())
        return 0 if result["mechanical_preflight"] == "COMPLETE" else 1
    except Invalid as error:
        code = str(error)
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        code = "INVALID_INPUT"
    sys.stderr.write(canonical({"mechanical_preflight": "UNKNOWN", "gate_authority": "NONE", "code": code}).decode())
    return 2


if __name__ == "__main__":
    sys.exit(main())
