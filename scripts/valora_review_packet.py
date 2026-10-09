"""Offline review packet v2. See the bounded review packet contract in docs/plan."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

VERSION = "2.0"
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z")
SUFFIXES = {".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".yaml", ".yml",
            ".toml", ".rs", ".ts", ".tsx", ".js", ".jsx", ".css", ".html",
            ".sql", ".sh", ".ps1", ".ini", ".cfg"}
MANDATORY = {"CODEX.md", "ENGINEERING_GUARDRAILS.md"}
MAX_INVENTORY_BYTES = 2_000_000


class Blocked(ValueError):
    """Only constant, privacy-safe error codes may leave the CLI."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise Blocked("INVALID_ARGUMENTS")


def require(condition, code):
    if not condition:
        raise Blocked(code)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def decode_json(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise Blocked("INVALID_JSON") from None


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys.split()), "INVALID_SCHEMA")


def safe_path(path):
    require(type(path) is str and PATH.fullmatch(path) is not None, "UNSAFE_PATH")
    parts = path.split("/")
    for part in parts:
        lower = part.lower()
        require(part not in {".", ".."} and not part.endswith("."), "UNSAFE_PATH")
        require(not re.fullmatch(r"(?:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", lower),
                "UNSAFE_PATH")
        require(lower not in {".git", ".ssh", ".aws", "private", "credentials",
                              "transcripts", "customer-data", "client-data", "secrets"}
                and not lower.startswith(".env"), "PRIVATE_SOURCE")
    require(Path(path).suffix.lower() in SUFFIXES, "UNSUPPORTED_FILE")
    require(not re.search(r"(?:^|/)(?:auth|credentials|secrets)(?:\.|$)", path.lower()),
            "PRIVATE_SOURCE")
    return path


def source_lines(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise Blocked("INVALID_UTF8") from None
    require(not text.startswith("\ufeff"), "AMBIGUOUS_ENCODING")
    require(not any((ord(char) < 32 and char not in "\t\r\n")
                    or 127 <= ord(char) <= 159 or char in "\u2028\u2029"
                    for char in text), "UNSUPPORTED_BINARY")
    crlf = raw.count(b"\r\n")
    require(raw.count(b"\r") == crlf and (not crlf or raw.count(b"\n") == crlf),
            "AMBIGUOUS_NEWLINES")
    # Obvious credentials block; human source review remains required, not inferred.
    require(not re.search(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}", raw),
            "PRIVATE_SOURCE")
    lines = raw.splitlines(keepends=True)
    return lines, "CRLF" if crlf else "LF" if b"\n" in raw else "NONE"


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.env = {key: value for key, value in os.environ.items()
                    if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "TEMP", "TMP"}}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                        GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
                        GIT_ATTR_NOSYSTEM="1", LC_ALL="C")
        actual = Path(self.git("rev-parse", "--show-toplevel").decode().strip()).resolve()
        require(actual == self.root, "REPOSITORY_ROOT_REQUIRED")
        # Status can execute clean filters; refuse them before inspecting the worktree.
        keys = self.git("config", "--includes", "--name-only", "--list").decode().splitlines()
        require(not any(key.lower().startswith("filter.") for key in keys), "UNSAFE_GIT_FILTER")

    def git(self, *args):
        try:
            result = subprocess.run(
                ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c",
                 "core.attributesFile=" + os.devnull, "-c", "protocol.allow=never", "-C", str(self.root), *args],
                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
                check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise Blocked("GIT_UNAVAILABLE") from None
        require(result.returncode == 0, "GIT_READ_FAILED")
        return result.stdout

    def current(self, base, head, branch):
        for commit in (base, head):
            require(type(commit) is str and SHA.fullmatch(commit) is not None, "INVALID_SHA")
            require(self.git("cat-file", "-t", commit) == b"commit\n", "COMMIT_REQUIRED")
        require(self.git("rev-parse", "HEAD").decode().strip() == head, "STALE_HEAD")
        require(type(branch) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]*", branch)
                is not None, "INVALID_BRANCH")
        require(self.git("symbolic-ref", "--short", "HEAD").decode().strip() == branch,
                "BRANCH_MISMATCH")
        require(self.git("merge-base", base, head).decode().strip() == base, "BASE_NOT_ANCESTOR")
        require(not self.git("status", "--porcelain=v1", "--untracked-files=all",
                             "--ignore-submodules=all"), "UNCLEAN_WORKTREE")

    def changes(self, base, head):
        fields = self.git("diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                          "--name-status", "-z", base, head, "--").split(b"\0")
        require(fields.pop() == b"" and len(fields) % 2 == 0, "INVALID_DIFF")
        result = []
        for index in range(0, len(fields), 2):
            status = fields[index].decode("ascii")
            require(status in {"A", "M", "D", "T"}, "UNSUPPORTED_CHANGE")
            path = safe_path(fields[index + 1].decode("utf-8"))
            result.append({"path": path, "status": status,
                           "revision": "base" if status == "D" else "head"})
        require(bool(result), "NO_CHANGED_FILES")
        return sorted(result, key=lambda row: row["path"])

    def blob(self, commit, path):
        entry = self.git("ls-tree", "-z", commit, "--", path).split(b"\0")
        require(len(entry) == 2 and entry[1] == b"", "MISSING_SOURCE")
        info, actual_path = entry[0].split(b"\t", 1)
        mode, kind, blob = info.decode("ascii").split()
        require(actual_path.decode("utf-8") == path, "MISSING_SOURCE")
        require(mode in {"100644", "100755"} and kind == "blob", "UNSUPPORTED_GIT_MODE")
        raw = self.git("cat-file", "blob", blob)
        identity = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                usedforsecurity=False).hexdigest()
        require(identity == blob, "GIT_BLOB_MISMATCH")
        return blob, mode, raw


def validate_inventory(inventory):
    shape(inventory, "schema_version task_id base_sha head_sha branch public_source_reviewed sources authorities")
    require(inventory["schema_version"] == VERSION, "UNSUPPORTED_VERSION")
    require(inventory["public_source_reviewed"] is True, "SOURCE_REVIEW_REQUIRED")
    require(type(inventory["task_id"]) is str and re.fullmatch(r"VALORA-TASK-[A-Z0-9-]{1,100}",
                                                              inventory["task_id"]), "INVALID_TASK")
    require(type(inventory["sources"]) is list and type(inventory["authorities"]) is list,
            "INVALID_SCHEMA")
    sources = {}
    folded = set()
    for row in inventory["sources"]:
        shape(row, "path revision blob_sha sha256 bytes lines")
        path = safe_path(row["path"])
        require(path.casefold() not in folded, "DUPLICATE_PATH")
        folded.add(path.casefold())
        require(row["revision"] in ("base", "head"), "INVALID_REVISION")
        require(type(row["blob_sha"]) is str and SHA.fullmatch(row["blob_sha"]), "INVALID_SHA")
        require(type(row["sha256"]) is str and DIGEST.fullmatch(row["sha256"]), "INVALID_HASH")
        require(all(type(row[key]) is int and row[key] >= 0 for key in ("bytes", "lines")),
                "INVALID_COUNTS")
        sources[path] = row
    authorities = {}
    for row in inventory["authorities"]:
        shape(row, "path tier spans")
        path = safe_path(row["path"])
        require(path not in authorities, "DUPLICATE_AUTHORITY")
        require(path in sources and sources[path]["revision"] == "head", "MISSING_AUTHORITY")
        require(row["tier"] in ("C1", "C2"), "INVALID_TIER")
        require(type(row["spans"]) is list and bool(row["spans"]), "MISSING_AUTHORITY_SPANS")
        for span in row["spans"]:
            require(type(span) is list and len(span) == 2
                    and all(type(number) is int for number in span)
                    and 1 <= span[0] <= span[1] <= sources[path]["lines"], "INVALID_RANGE")
        ordered = sorted(row["spans"])
        require(all(left[1] < right[0] for left, right in zip(ordered, ordered[1:])),
                "OVERLAPPING_RANGES")
        authorities[path] = {**row, "spans": ordered}
    require(MANDATORY <= authorities.keys(), "MISSING_GOVERNING_AUTHORITY")
    return sources, authorities


def build(repo, inventory, mode, escalation=None):
    require(mode in ("full", "scoped"), "INVALID_MODE")
    require(escalation in (None, "CONTEXT_INSUFFICIENT") and (not escalation or mode == "full"),
            "INVALID_ESCALATION")
    sources, authorities = validate_inventory(inventory)
    base, head = inventory["base_sha"], inventory["head_sha"]
    repo.current(base, head, inventory["branch"])
    changes = repo.changes(base, head)
    changed = {row["path"]: row for row in changes}
    require(set(sources) == set(changed) | set(authorities), "SOURCE_COVERAGE_MISMATCH")
    for path, change in changed.items():
        require(sources[path]["revision"] == change["revision"], "SOURCE_REVISION_MISMATCH")
        # Check both sides: a replaced/deleted symlink or binary must not disappear from evidence.
        if change["status"] != "A":
            _, _, before = repo.blob(base, path)
            source_lines(before)
    contents, metadata = {}, []
    for path, row in sorted(sources.items()):
        commit = head if row["revision"] == "head" else base
        blob, git_mode, raw = repo.blob(commit, path)
        lines, endings = source_lines(raw)
        require((blob, sha256(raw), len(raw), len(lines)) ==
                (row["blob_sha"], row["sha256"], row["bytes"], row["lines"]), "SOURCE_IDENTITY_MISMATCH")
        contents[path] = (raw, lines)
        metadata.append({**row, "commit_sha": commit, "git_mode": git_mode, "newlines": endings})
    normalized = {**inventory, "sources": [sources[path] for path in sorted(sources)],
                  "authorities": [authorities[path] for path in sorted(authorities)]}
    header = {"schema_version": VERSION, "task_id": inventory["task_id"], "base_sha": base,
              "head_sha": head, "mode": mode, "escalation": escalation,
              "inventory_sha256": sha256(canonical(normalized)), "changes": changes,
              "authorities": normalized["authorities"], "sources": metadata}
    packet = bytearray(b"VALORA REVIEW PACKET v2\n" + canonical(header))
    segments = []
    for path in sorted(sources):
        raw, lines = contents[path]
        is_full = path in changed or mode == "full"
        ranges = [[1, len(lines)]] if is_full and lines else [[0, 0]] if is_full else authorities[path]["spans"]
        for start, end in ranges:
            payload = raw if is_full else b"".join(lines[start - 1:end])
            source_offset = sum(map(len, lines[:start - 1])) if start else 0
            segment = {"index": len(segments), "path": path, "revision": sources[path]["revision"],
                       "blob_sha": sources[path]["blob_sha"], "line_start": start, "line_end": end,
                       "source_offset": source_offset, "bytes": len(payload), "sha256": sha256(payload),
                       "complete_file": is_full}
            packet.extend(b"BEGIN SEGMENT " + canonical(segment))
            segment["packet_offset"] = len(packet)
            packet.extend(payload)
            packet.extend(b"\nEND SEGMENT " + str(segment["index"]).encode() + b"\n")
            if is_full:
                packet.extend(b"COMPLETE FILE " + path.encode("ascii") + b"\n")
            segments.append(segment)
    packet.extend(b"END PACKET\n")
    result = bytes(packet)
    manifest = {**header, "coverage": {"changed_files_complete": True,
                                       "declared_authorities_complete": True,
                                       "authority_selection": "HUMAN_REVIEWED_INPUT",
                                       "gate_authority": "NONE"},
                "segments": segments, "packet_bytes": len(result), "packet_sha256": sha256(result)}
    # Recheck after all object reads, before returning any deliverable.
    repo.current(base, head, inventory["branch"])
    return result, canonical(manifest)


def read_regular(path, limit=None):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), "REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read() if limit is None else stream.read(limit + 1)
    require(limit is None or len(raw) <= limit, "INVENTORY_TOO_LARGE")
    return raw


def verify(repo, inventory, packet, manifest):
    claimed = decode_json(manifest)
    require(type(claimed) is dict, "INVALID_MANIFEST")
    expected_packet, expected_manifest = build(repo, inventory, claimed.get("mode"), claimed.get("escalation"))
    require(manifest == expected_manifest and packet == expected_packet, "PACKET_VERIFICATION_FAILED")
    return sha256(packet)


def main(argv=None):
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("build", "verify"))
    parser.add_argument("--repo", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--inventory-sha256", required=True,
                        help="SHA-256 of the exact externally reviewed inventory file bytes")
    parser.add_argument("--mode", choices=("full", "scoped"))
    parser.add_argument("--escalate", choices=("CONTEXT_INSUFFICIENT",))
    parser.add_argument("--packet", required=True)
    parser.add_argument("--manifest", required=True)
    try:
        args = parser.parse_args(argv)
        raw = read_regular(args.inventory, MAX_INVENTORY_BYTES)
        require(sha256(raw) == args.inventory_sha256, "INVENTORY_HASH_MISMATCH")
        inventory = decode_json(raw)
        repo = Repository(args.repo)
        if args.operation == "verify":
            require(args.mode is None and args.escalate is None, "INVALID_VERIFY_OPTIONS")
            digest = verify(repo, inventory, read_regular(args.packet), read_regular(args.manifest))
        else:
            destinations = [Path(args.packet), Path(args.manifest)]
            protected = [repo.root]
            for flag in ("--absolute-git-dir", "--git-common-dir"):
                location = Path(repo.git("rev-parse", flag).decode().strip())
                protected.append((repo.root / location).resolve())
            resolved = [path.resolve() for path in destinations]
            require(len(set(resolved)) == 2, "OUTPUT_COLLISION")
            for path, target in zip(destinations, resolved):
                require(not path.exists() and not path.is_symlink() and path.parent.is_dir(), "OUTPUT_EXISTS_OR_INVALID")
                require(target != Path(args.inventory).resolve()
                        and all(not target.is_relative_to(root) for root in protected), "SOURCE_WRITE_FORBIDDEN")
            packet, manifest = build(repo, inventory, args.mode, args.escalate)
            # Exclusive creation prevents overwrites. IO failures can leave incomplete outputs.
            for path, data in zip(destinations, (packet, manifest)):
                with path.open("xb") as stream:
                    stream.write(data)
            digest = sha256(packet)
        sys.stdout.buffer.write(canonical({"status": "VERIFIED_BYTES", "packet_sha256": digest,
                                           "gate_authority": "NONE"}))
        return 0
    except Blocked as error:
        sys.stderr.buffer.write(canonical({"status": "BLOCKED", "code": str(error)}))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        sys.stderr.buffer.write(canonical({"status": "BLOCKED", "code": "INVALID_INPUT_OR_IO"}))
    return 2


if __name__ == "__main__":
    sys.exit(main())
