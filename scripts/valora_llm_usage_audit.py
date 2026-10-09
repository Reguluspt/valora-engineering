#!/usr/bin/env python3
"""Offline sanitized metadata audit; see VALORA_PM_OPS_004_METRICS_CONTRACT.md."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

VERSION = "1.0"
MAX_BYTES = 2_000_000
MAX_EVENTS = 2000
COUNTERS = ("input", "cached", "cache_write", "output", "reasoning", "total")
MODELS = {
    "gpt-6-luna", "gpt-6-astra", "gpt-6.1-sol", "deepseek-v4.1-flash",
    "opencode-go/deepseek-v4.1-flash", "gemini-3.1-pro-high", "UNKNOWN",
}
FORMATS = {
    "deepseek_chat": ("deepseek", "INCLUDES_READ"),
    "gemini_generate": ("google", "INCLUDES_READ"),
    "openai_responses": ("openai", "INCLUDES_READ_WRITE"),
    "codex_metadata": ("openai", "UNKNOWN"),
    "runner_metadata": (None, "UNKNOWN"),
}
EVENT_FIELDS = {
    "event_id", "task_id", "issue", "pr", "base_sha", "candidate_sha", "packet_sha256",
    "packet_bytes", "provider", "model", "model_identity", "session_id", "phase", "attempt",
    "sequence", "timestamp", "snapshot_kind", "origin", "usage_format", "usage_source",
    "usage", "finish_reason", "report_state", "quality", "elapsed_ms", "cost",
}
CSV_FIELDS = (
    "event_id", "task_id", "issue", "pr", "base_sha", "candidate_sha", "packet_sha256",
    "packet_bytes", "provider", "model", "model_identity", "session_sha256", "phase", "attempt",
    "sequence", "timestamp", "snapshot_kind", "origin", "usage_format", "usage_source",
    "cache_semantics", "finish_reason", "report_state", "quality", "elapsed_ms", "status",
    "review_completeness", "input", "cached", "cache_write", "output", "reasoning", "total",
    "uncached", "cost_classification", "cost_amount", "cost_currency", "cost_source", "warnings",
)


class Blocked(Exception):
    """Only constant error codes are safe to disclose."""


class MetadataParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, '{"status":"BLOCKED","code":"INVALID_ARGUMENTS"}\n')


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Blocked(code)


def shape(value: object, required: set[str], optional: set[str] | None = None) -> dict:
    require(isinstance(value, dict), "OBJECT_REQUIRED")
    require(required <= value.keys(), "MISSING_FIELD")
    require(value.keys() <= required | (optional or set()), "UNEXPECTED_FIELD")
    return value


def integer(value: object, nullable: bool = False) -> None:
    require((nullable and value is None) or (type(value) is int and 0 <= value <= 10**15),
            "INVALID_COUNTER")


def match(value: object, pattern: str) -> None:
    require(isinstance(value, str) and re.fullmatch(pattern, value) is not None,
            "INVALID_METADATA")


def native_usage(event: dict) -> tuple[dict, str]:
    fmt = event["usage_format"]
    provider, semantics = FORMATS[fmt]
    require(provider is None or provider == event["provider"], "PROVIDER_FORMAT_MISMATCH")
    usage = event["usage"]
    fields = {
        "deepseek_chat": {
            "prompt_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
            "completion_tokens", "reasoning_tokens", "total_tokens",
        },
        "gemini_generate": {
            "promptTokenCount", "cachedContentTokenCount", "candidatesTokenCount",
            "thoughtsTokenCount", "totalTokenCount",
        },
        "openai_responses": {
            "input_tokens", "cached_tokens", "cache_write_tokens", "output_tokens",
            "reasoning_tokens", "total_tokens",
        },
        "codex_metadata": {
            "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
            "output_tokens", "reasoning_output_tokens", "total_tokens",
        },
        "runner_metadata": set(COUNTERS),
    }[fmt]
    shape(usage, set(), fields)
    for value in usage.values():
        integer(value, nullable=True)
    keys = {
        "deepseek_chat": ("prompt_tokens", "prompt_cache_hit_tokens", None,
                          "completion_tokens", "reasoning_tokens", "total_tokens"),
        "gemini_generate": ("promptTokenCount", "cachedContentTokenCount", None,
                            "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount"),
        "openai_responses": ("input_tokens", "cached_tokens", "cache_write_tokens",
                             "output_tokens", "reasoning_tokens", "total_tokens"),
        "codex_metadata": ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
                           "output_tokens", "reasoning_output_tokens", "total_tokens"),
        "runner_metadata": COUNTERS,
    }[fmt]
    counters = dict(zip(COUNTERS, (usage.get(key) if key else None for key in keys)))
    inp, cache, write, out, reasoning, total = (counters[key] for key in COUNTERS)
    if semantics != "UNKNOWN" and inp is not None and cache is not None:
        require(cache <= inp, "CACHE_EXCEEDS_INPUT")
        if semantics == "INCLUDES_READ_WRITE" and write is not None:
            require(cache + write <= inp, "CACHE_EXCEEDS_INPUT")
    if fmt == "deepseek_chat" and usage.get("prompt_cache_miss_tokens") is not None:
        if inp is not None and cache is not None:
            require(inp == cache + usage["prompt_cache_miss_tokens"], "CACHE_SPLIT_MISMATCH")
    if fmt in {"deepseek_chat", "openai_responses", "codex_metadata"}:
        if out is not None and reasoning is not None:
            require(reasoning <= out, "REASONING_EXCEEDS_OUTPUT")
        if inp is not None and out is not None and total is not None:
            require(total == inp + out, "TOTAL_MISMATCH")
    if fmt == "gemini_generate" and all(x is not None for x in (inp, out, reasoning, total)):
        require(total == inp + out + reasoning, "TOTAL_MISMATCH")
    return counters, semantics


def validate_event(event: object) -> dict:
    event = shape(event, EVENT_FIELDS)
    match(event["event_id"], r"e-[0-9a-f]{8}")
    match(event["task_id"], r"VALORA-TASK-[A-Z0-9-]{1,100}")
    for key in ("issue", "pr", "packet_bytes", "attempt", "sequence"):
        integer(event[key])
        require(event[key] > 0, "INVALID_METADATA")
    for key in ("base_sha", "candidate_sha"):
        match(event[key], r"[0-9a-f]{40}")
    match(event["packet_sha256"], r"[0-9a-f]{64}")
    require(event["provider"] in {"openai", "deepseek", "google", "UNKNOWN"}, "UNKNOWN_PROVIDER")
    require(event["model"] in MODELS, "UNSUPPORTED_MODEL")
    model_provider = "openai" if event["model"].startswith("gpt-") else \
        "google" if event["model"].startswith("gemini-") else \
        "deepseek" if "deepseek" in event["model"] else None
    require(model_provider is None or model_provider == event["provider"], "MODEL_PROVIDER_MISMATCH")
    require(event["model_identity"] in {"NATIVE_REPORTED", "ACTUAL_MODEL_UNVERIFIED"},
            "INVALID_MODEL_IDENTITY")
    match(event["session_id"], r"[A-Za-z0-9_-]{1,128}")
    require(event["phase"] in {"preflight", "review", "implementation", "adjudication"},
            "INVALID_PHASE")
    require(event["snapshot_kind"] in {"per_turn", "cumulative", "delta"}, "INVALID_SNAPSHOT")
    require(event["origin"] in {None, "ZERO", "UNAVAILABLE"} or
            (isinstance(event["origin"], str) and
             re.fullmatch(r"e-[0-9a-f]{8}", event["origin"])), "INVALID_ORIGIN")
    require(event["usage_format"] in FORMATS, "UNKNOWN_USAGE_FORMAT")
    match(event["usage_source"], r"SYNTHETIC|https://github\.com/Reguluspt/valora-engineering/"
          r"(?:pull|issues)/[0-9]+#issuecomment-[0-9]+")
    match(event["timestamp"], r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z")
    try:
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        raise Blocked("INVALID_TIMESTAMP") from None
    require(event["finish_reason"] in {
        "stop", "length", "STOP", "MAX_TOKENS", "completed", "incomplete", "UNKNOWN",
        "content_filter", "SAFETY", "error", "tool_calls",
    }, "UNKNOWN_FINISH_REASON")
    require(event["report_state"] in {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE", "UNKNOWN"},
            "INVALID_REPORT_STATE")
    require(event["quality"] in {"REPORTED_PASS", "REPORTED_FINDINGS", "NOT_EVALUATED"},
            "INVALID_QUALITY")
    integer(event["elapsed_ms"], nullable=True)
    if event["cost"] is not None:
        cost = shape(event["cost"], {"amount", "currency", "source", "original_charge"})
        match(cost["amount"], r"(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,8})?")
        match(cost["currency"], r"[A-Z]{3}")
        match(cost["source"], r"billing-[0-9a-f]{64}")
        require(cost["original_charge"] is True, "UNVERIFIED_COST")
        try:
            require(Decimal(cost["amount"]).is_finite(), "INVALID_COST")
        except InvalidOperation:
            raise Blocked("INVALID_COST") from None
        require(event["snapshot_kind"] != "cumulative", "CUMULATIVE_COST_UNSUPPORTED")
    return event


def audit(events: list[dict], expected_head: str | None = None,
          expected_packet: str | None = None) -> dict:
    require(isinstance(events, list) and 0 < len(events) <= MAX_EVENTS, "INVALID_EVENT_COUNT")
    events = [validate_event(event) for event in events]
    require(len({event["event_id"] for event in events}) == len(events), "DUPLICATE_EVENT")
    streams: dict[tuple, list] = {}
    task_bindings = {}
    for event in events:
        binding = tuple(event[key] for key in
                        ("issue", "pr", "base_sha", "candidate_sha", "packet_sha256", "packet_bytes"))
        require(task_bindings.setdefault(event["task_id"], binding) == binding,
                "TASK_IDENTITY_CHANGED")
        if expected_head:
            require(event["candidate_sha"] == expected_head, "HEAD_MISMATCH")
        if expected_packet:
            require(event["packet_sha256"] == expected_packet, "PACKET_MISMATCH")
        key = (event["task_id"], event["provider"], event["session_id"])
        streams.setdefault(key, []).append(event)
    rows = []
    for stream in streams.values():
        stream.sort(key=lambda event: event["sequence"])
        require(len({event["sequence"] for event in stream}) == len(stream), "DUPLICATE_SEQUENCE")
        identity_fields = ("issue", "pr", "base_sha", "candidate_sha", "packet_sha256",
                           "packet_bytes", "model", "model_identity", "usage_format", "usage_source",
                           "snapshot_kind")
        first = stream[0]
        require(all(all(event[key] == first[key] for key in identity_fields) for event in stream),
                "STREAM_IDENTITY_CHANGED")
        if first["snapshot_kind"] == "delta":
            require(len({event["origin"] for event in stream}) == len(stream),
                    "DUPLICATE_DELTA_ORIGIN")
        previous = None
        previous_raw = None
        for event in stream:
            raw, semantics = native_usage(event)
            warnings = []
            if event["provider"] == "UNKNOWN" or semantics == "UNKNOWN":
                warnings.append("CACHE_SEMANTICS_UNKNOWN")
            if event["model_identity"] == "ACTUAL_MODEL_UNVERIFIED":
                warnings.append("ACTUAL_MODEL_UNVERIFIED")
            if previous:
                require(datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")) >
                        datetime.fromisoformat(previous["timestamp"].replace("Z", "+00:00")),
                        "NONMONOTONIC_TIMESTAMP")
            kind = event["snapshot_kind"]
            measured = raw.copy()
            if kind == "per_turn":
                require(event["origin"] is None, "INVALID_ORIGIN")
            elif kind == "delta":
                require(isinstance(event["origin"], str) and
                        re.fullmatch(r"e-[0-9a-f]{8}", event["origin"]) is not None,
                        "MISSING_DELTA_ORIGIN")
                warnings.append("SOURCE_REPORTED_DELTA_NOT_RECONSTRUCTED")
            elif previous is None:
                require(event["origin"] in {"ZERO", "UNAVAILABLE"}, "MISSING_CUMULATIVE_ORIGIN")
                if event["origin"] == "UNAVAILABLE":
                    measured = dict.fromkeys(COUNTERS)
                    warnings.append("MISSING_ZERO_ORIGIN_BASELINE_ONLY")
            else:
                require(event["origin"] == previous["event_id"], "BROKEN_CUMULATIVE_CHAIN")
                for key in COUNTERS:
                    old, new = previous_raw[key], raw[key]
                    if old is not None and new is not None:
                        require(new >= old, "NONMONOTONIC_COUNTER")
                        measured[key] = new - old
                    else:
                        measured[key] = None
                if raw == previous_raw:
                    warnings.append("REPEATED_SNAPSHOT_ZERO_CONTRIBUTION")
            inp, cache, write = (measured[key] for key in ("input", "cached", "cache_write"))
            if event["usage_format"] in {"deepseek_chat", "openai_responses", "codex_metadata"}:
                out, reasoning = measured["output"], measured["reasoning"]
                if out is not None and reasoning is not None:
                    require(reasoning <= out, "REASONING_DELTA_EXCEEDS_OUTPUT")
            uncached = None
            if inp is not None and cache is not None and semantics == "INCLUDES_READ":
                require(cache <= inp, "CACHE_DELTA_EXCEEDS_INPUT")
                uncached = inp - cache
            if all(value is not None for value in (inp, cache, write)) and \
                    semantics == "INCLUDES_READ_WRITE":
                require(cache + write <= inp, "CACHE_DELTA_EXCEEDS_INPUT")
                uncached = inp - cache - write
            if any(value is None for value in measured.values()) or uncached is None:
                warnings.append("PARTIAL_TOKEN_MEASUREMENT")
            terminal = event["finish_reason"] in {"stop", "STOP", "completed"}
            completeness = "COMPLETE" if terminal and event["report_state"] == "COMPLETE" \
                else "INCOMPLETE" if event["finish_reason"] in {
                    "length", "MAX_TOKENS", "incomplete", "error", "content_filter", "SAFETY",
                } or event["report_state"] == "INCOMPLETE" else "UNKNOWN"
            if event["phase"] == "review" and completeness != "COMPLETE":
                warnings.append("REVIEW_NOT_COMPLETE")
            cost = event["cost"]
            if cost is None:
                warnings.append("COST_NOT_MEASURABLE")
            row = {key: event[key] for key in CSV_FIELDS if key in event and key != "cost"}
            row.update(session_sha256=hashlib.sha256(event["session_id"].encode()).hexdigest(),
                       cache_semantics=semantics, review_completeness=completeness,
                       uncached=uncached, warnings=sorted(set(warnings)),
                       status="WARN" if warnings else "OBSERVED",
                       cost_classification="SOURCE_ASSERTED_ORIGINAL_CHARGE" if cost else
                       "NOT MEASURABLE", cost_amount=cost["amount"] if cost else None,
                       cost_currency=cost["currency"] if cost else None,
                       cost_source=cost["source"] if cost else None)
            row.update(measured)
            rows.append(row)
            previous, previous_raw = event, raw
    rows.sort(key=lambda row: (row["task_id"], row["provider"], row["session_sha256"],
                               row["sequence"], row["event_id"]))
    groups = {}
    for row in rows:
        key = (row["task_id"], row["provider"], row["session_sha256"], row["phase"])
        groups.setdefault(key, []).append(row)
    summaries = []
    for key, members in sorted(groups.items()):
        summary = dict(zip(("task_id", "provider", "session_sha256", "phase"), key))
        summary["events"] = len(members)
        for counter in (*COUNTERS, "uncached"):
            values = [member[counter] for member in members]
            summary[counter] = sum(values) if all(value is not None for value in values) else None
        summary["cost_classification"] = "NOT COMPARABLE"
        summaries.append(summary)
    return {"schema_version": VERSION, "status": "WARN" if any(row["warnings"] for row in rows)
            else "OBSERVED", "gate_authority": "NONE", "comparison": "NOT COMPARABLE",
            "rows": rows, "phase_totals": summaries}


def unique_object(pairs: list[tuple]) -> dict:
    obj = {}
    for key, value in pairs:
        require(key not in obj, "DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def read_metadata(path: Path) -> list[dict]:
    require(path.suffix.lower() in {".json", ".jsonl"}, "METADATA_EXTENSION_REQUIRED")
    require(path.is_file() and not path.is_symlink(), "REGULAR_METADATA_FILE_REQUIRED")
    with path.open("rb") as source:
        raw = source.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "INPUT_TOO_LARGE")
    try:
        content = raw.decode("utf-8")
        if path.suffix.lower() == ".jsonl":
            documents = [json.loads(line, object_pairs_hook=unique_object)
                         for line in content.splitlines() if line.strip()]
            events = []
            for document in documents:
                shape(document, {"schema_version", "sanitized_metadata", "event"})
                require(document["schema_version"] == VERSION and
                        document["sanitized_metadata"] is True, "SANITIZED_SCHEMA_REQUIRED")
                events.append(document["event"])
            return events
        document = json.loads(content, object_pairs_hook=unique_object)
        shape(document, {"schema_version", "sanitized_metadata", "events"})
        require(document["schema_version"] == VERSION and document["sanitized_metadata"] is True,
                "SANITIZED_SCHEMA_REQUIRED")
        return document["events"]
    except (UnicodeError, ValueError, RecursionError):
        raise Blocked("INVALID_METADATA_JSON") from None


def json_report(report: dict) -> str:
    return json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n"


def csv_report(report: dict) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in report["rows"]:
        values = {key: row[key] for key in CSV_FIELDS}
        values["warnings"] = "|".join(values["warnings"])
        writer.writerow(values)
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = MetadataParser(description=__doc__)
    parser.add_argument("input", type=Path, help="explicit sanitized JSON/JSONL metadata file")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-packet")
    args = parser.parse_args(argv)
    try:
        if args.expected_head is not None:
            match(args.expected_head, r"[0-9a-f]{40}")
        if args.expected_packet is not None:
            match(args.expected_packet, r"[0-9a-f]{64}")
        outputs = [path for path in (args.json_out, args.csv_out) if path is not None]
        resolved = [path.resolve() for path in outputs]
        require(len(set(resolved)) == len(resolved), "OUTPUT_COLLISION")
        require(all(path != args.input.resolve() for path in resolved), "INPUT_OUTPUT_COLLISION")
        require(all(not path.exists() for path in outputs), "OUTPUT_ALREADY_EXISTS")
        require(all(path.parent.is_dir() for path in outputs), "OUTPUT_PARENT_REQUIRED")
        report = audit(read_metadata(args.input), args.expected_head, args.expected_packet)
        rendered = [(args.json_out, json_report(report)), (args.csv_out, csv_report(report))]
        for path, content in rendered:
            if path is not None:
                with path.open("x", encoding="utf-8", newline="") as destination:
                    destination.write(content)
        if args.json_out is None:
            sys.stdout.write(json_report(report))
        return 1 if report["status"] == "WARN" else 0
    except Blocked as error:
        sys.stderr.write(json_report({"status": "BLOCKED", "code": str(error)}))
        return 2
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        sys.stderr.write(json_report({"status": "BLOCKED", "code": "IO_OR_METADATA_ERROR"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
