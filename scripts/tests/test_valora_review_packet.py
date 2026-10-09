"""Byte provenance and executable offline CLI tests in synthetic Git repositories."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "valora_review_packet.py"
FIXTURES = Path(__file__).parent / "fixtures" / "valora_review_packet"
spec = importlib.util.spec_from_file_location("review_packet", SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def git(root, *args, data=None):
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="Synthetic Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="Synthetic Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
               GIT_AUTHOR_DATE="2026-01-01T00:00:00+00:00", GIT_COMMITTER_DATE="2026-01-01T00:00:00+00:00")
    return subprocess.check_output(["git", "-C", str(root), *args], input=data, env=env,
                                   stderr=subprocess.PIPE)


def commit(root, message):
    git(root, "add", "--", *sorted(path.name for path in root.iterdir() if path.is_file()))
    git(root, "commit", "--no-gpg-sign", "-m", message)
    return git(root, "rev-parse", "HEAD").decode().strip()


def inventory(root, base, head):
    # Independent fixture inventory creation; source content is never reconstructed by the builder here.
    rows = []
    changes = git(root, "diff", "--no-renames", "--name-status", "-z", base, head).split(b"\0")[:-1]
    revisions = {changes[index + 1].decode(): "base" if changes[index] == b"D" else "head"
                 for index in range(0, len(changes), 2)}
    authorities = [{"path": "CODEX.md", "tier": "C1", "spans": [[2, 3]]},
                   {"path": "ENGINEERING_GUARDRAILS.md", "tier": "C1", "spans": [[1, 2]]},
                   {"path": "contract.md", "tier": "C2", "spans": [[2, 2], [4, 4]]}]
    for authority in authorities:
        revisions[authority["path"]] = "head"
    for path, revision in sorted(revisions.items()):
        sha = head if revision == "head" else base
        blob = git(root, "rev-parse", f"{sha}:{path}").decode().strip()
        raw = git(root, "cat-file", "blob", blob)
        rows.append({"path": path, "revision": revision, "blob_sha": blob,
                     "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                     "lines": len(raw.splitlines(keepends=True))})
    return {"schema_version": "2.0", "task_id": "VALORA-TASK-FIXTURE", "base_sha": base,
            "head_sha": head, "branch": "fixture", "public_source_reviewed": True,
            "sources": rows, "authorities": authorities}


def create_fixture(root):
    root.mkdir()
    git(root, "init", "--initial-branch=fixture", "--object-format=sha1")
    git(root, "config", "core.autocrlf", "false")
    git(root, "config", "core.filemode", "false")
    initial = {"CODEX.md": b"# Synthetic rules\nBinding A\nBinding B\nOther context\n",
               "ENGINEERING_GUARDRAILS.md": b"# Guardrails\nNo private data\nOther context\n",
               "contract.md": b"# Contract\nRequired C2 one\nContext\nRequired C2 two\n",
               "changed.py": b"print('before')\n", "removed.txt": b"Deleted source\n"}
    for name, raw in initial.items():
        (root / name).write_bytes(raw)
    base = commit(root, "synthetic baseline")
    (root / "changed.py").write_bytes("# Văn bản\nprint('after')\n".encode())
    (root / "notes.txt").write_bytes(b"First\r\nSecond\r\nLast without newline")
    (root / "empty.txt").write_bytes(b"")
    git(root, "rm", "--", "removed.txt")
    head = commit(root, "synthetic candidate")
    return inventory(root, base, head)


class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_dir = tempfile.TemporaryDirectory()
        cls.template = Path(cls.template_dir.name) / "repo"
        cls.template_inventory = create_fixture(cls.template)

    @classmethod
    def tearDownClass(cls):
        cls.template_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        shutil.copytree(self.template, self.root)
        self.repo = builder.Repository(self.root)
        self.input = copy.deepcopy(self.template_inventory)

    def build(self, mode="scoped"):
        return builder.build(self.repo, self.input, mode)

    def blocked(self, code):
        return self.assertRaisesRegex(builder.Blocked, "^" + code + "$")

    def cli(self, operation="build", mode="scoped", input_raw=None, digest=None,
            packet_path=None, manifest_path=None, extra=()):
        selected = Path(self.temp.name) / "inventory.json"
        raw = input_raw if input_raw is not None else builder.canonical(self.input)
        selected.write_bytes(raw)
        args = [sys.executable, str(SCRIPT), operation, "--repo", str(self.root), "--inventory",
                str(selected), "--inventory-sha256", digest or hashlib.sha256(raw).hexdigest(),
                "--packet", str(packet_path or Path(self.temp.name) / "packet.txt"),
                "--manifest", str(manifest_path or Path(self.temp.name) / "manifest.json")]
        if operation == "build":
            args.extend(["--mode", mode])
        return subprocess.run(args + list(extra), capture_output=True)

    def test_full_and_scoped_goldens(self):
        for mode in ("full", "scoped"):
            with self.subTest(mode=mode):
                packet, manifest = self.build(mode)
                golden = json.loads((FIXTURES / f"{mode}.packet.json").read_bytes())
                self.assertEqual(packet, bytes.fromhex(golden["packet_hex"]))
                golden_manifest = json.loads((FIXTURES / f"{mode}.manifest.json").read_bytes())
                self.assertEqual(manifest, builder.canonical(golden_manifest))

    def test_complete_changed_files_and_exact_span_reconstruction(self):
        for mode in ("full", "scoped"):
            packet, raw_manifest = self.build(mode)
            manifest = json.loads(raw_manifest)
            changed = {row["path"] for row in manifest["changes"]}
            complete = set()
            for segment in manifest["segments"]:
                payload = packet[segment["packet_offset"]:segment["packet_offset"] + segment["bytes"]]
                commit_sha = self.input["head_sha"] if segment["revision"] == "head" else self.input["base_sha"]
                original = git(self.root, "show", f"{commit_sha}:{segment['path']}")
                expected = original if segment["complete_file"] else b"".join(
                    original.splitlines(keepends=True)[segment["line_start"] - 1:segment["line_end"]])
                self.assertEqual(payload, expected)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), segment["sha256"])
                self.assertEqual(original[segment["source_offset"]:segment["source_offset"] + segment["bytes"]], payload)
                if segment["complete_file"]:
                    complete.add(segment["path"])
            self.assertTrue(changed <= complete)
            self.assertEqual(manifest["packet_sha256"], hashlib.sha256(packet).hexdigest())
            self.assertEqual(manifest["packet_bytes"], len(packet))
            self.assertEqual(raw_manifest, builder.canonical(json.loads(raw_manifest)))

    def test_inventory_order_does_not_change_output(self):
        before = self.build()
        self.input["sources"].reverse()
        self.input["authorities"].reverse()
        self.input["authorities"][0]["spans"].reverse()
        self.assertEqual(before, self.build())

    def test_cli_roundtrip_and_independent_parity(self):
        for mode in ("full", "scoped"):
            packet = Path(self.temp.name) / f"{mode}.txt"
            manifest = Path(self.temp.name) / f"{mode}.json"
            result = self.cli(mode=mode, packet_path=packet, manifest_path=manifest)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b"")
            self.assertEqual((packet.read_bytes(), manifest.read_bytes()), self.build(mode))
            result = self.cli(operation="verify", packet_path=packet, manifest_path=manifest)
            self.assertEqual(result.returncode, 0, result.stderr)
            second_packet, second_manifest = Path(self.temp.name) / f"{mode}-2.txt", Path(self.temp.name) / f"{mode}-2.json"
            self.assertEqual(self.cli(mode=mode, packet_path=second_packet, manifest_path=second_manifest).returncode, 0)
            self.assertEqual(packet.read_bytes(), second_packet.read_bytes())
            self.assertEqual(manifest.read_bytes(), second_manifest.read_bytes())

    def test_newline_bytes_and_empty_or_unterminated_lines(self):
        packet, raw_manifest = self.build()
        sources = {row["path"]: row for row in json.loads(raw_manifest)["sources"]}
        self.assertEqual(sources["notes.txt"]["newlines"], "CRLF")
        self.assertEqual(sources["empty.txt"]["lines"], 0)
        self.assertIn(b"First\r\nSecond\r\nLast without newline", packet)
        for raw, expected in ((b"", []), (b"a", [b"a"]), (b"a\n", [b"a\n"]),
                              (b"a\r\nb", [b"a\r\n", b"b"]), (b"a\nb\n", [b"a\n", b"b\n"])):
            self.assertEqual(builder.source_lines(raw)[0], expected)

    def test_full_escalation(self):
        packet, manifest = builder.build(self.repo, self.input, "full", "CONTEXT_INSUFFICIENT")
        self.assertEqual(json.loads(manifest)["escalation"], "CONTEXT_INSUFFICIENT")
        self.assertEqual(builder.verify(self.repo, self.input, packet, manifest), builder.sha256(packet))
        with self.blocked("INVALID_ESCALATION"):
            builder.build(self.repo, self.input, "scoped", "CONTEXT_INSUFFICIENT")

    def test_missing_changed_source(self):
        self.input["sources"] = [row for row in self.input["sources"] if row["path"] != "notes.txt"]
        with self.blocked("SOURCE_COVERAGE_MISMATCH"):
            self.build()

    def test_hash_blob_byte_and_line_mismatches(self):
        for key, value in (("sha256", "0" * 64), ("blob_sha", "0" * 40), ("bytes", 1), ("lines", 100)):
            with self.subTest(key=key):
                self.input = copy.deepcopy(self.template_inventory)
                row = next(row for row in self.input["sources"] if row["path"] == "changed.py")
                row[key] = value
                with self.blocked("SOURCE_IDENTITY_MISMATCH"):
                    self.build()

    def test_invalid_sha_and_blob_used_as_commit(self):
        self.input["head_sha"] = "main"
        with self.blocked("INVALID_SHA"):
            self.build()
        self.input["head_sha"] = self.input["sources"][0]["blob_sha"]
        with self.blocked("COMMIT_REQUIRED"):
            self.build()

    def test_stale_head(self):
        self.input["head_sha"] = self.input["base_sha"]
        with self.blocked("STALE_HEAD"):
            self.build()

    def test_wrong_branch(self):
        self.input["branch"] = "another"
        with self.blocked("BRANCH_MISMATCH"):
            self.build()

    def test_unclean_worktree(self):
        (self.root / "notes.txt").write_bytes(b"uncommitted\n")
        with self.blocked("UNCLEAN_WORKTREE"):
            self.build()

    def test_untracked_worktree(self):
        (self.root / "untracked.txt").write_bytes(b"untracked\n")
        with self.blocked("UNCLEAN_WORKTREE"):
            self.build()

    def test_source_drift_during_build(self):
        original = self.repo.blob
        changed = False

        def moving_source(sha, path):
            nonlocal changed
            result = original(sha, path)
            if not changed:
                changed = True
                (self.root / "drift.txt").write_bytes(b"drift\n")
            return result

        with patch.object(self.repo, "blob", moving_source), self.blocked("UNCLEAN_WORKTREE"):
            self.build()

    def test_missing_required_authority(self):
        self.input["authorities"] = [row for row in self.input["authorities"] if row["path"] != "CODEX.md"]
        with self.blocked("MISSING_GOVERNING_AUTHORITY"):
            self.build()

    def test_missing_declared_authority_source(self):
        self.input["sources"] = [row for row in self.input["sources"] if row["path"] != "contract.md"]
        with self.blocked("MISSING_AUTHORITY"):
            self.build()

    def test_duplicate_authority(self):
        self.input["authorities"].append(copy.deepcopy(self.input["authorities"][0]))
        with self.blocked("DUPLICATE_AUTHORITY"):
            self.build()

    def test_duplicate_and_case_colliding_sources(self):
        for path in ("CODEX.md", "codex.md"):
            self.input = copy.deepcopy(self.template_inventory)
            duplicate = copy.deepcopy(self.input["sources"][0])
            duplicate["path"] = path
            self.input["sources"].append(duplicate)
            with self.blocked("DUPLICATE_PATH"):
                self.build()

    def test_bad_ranges(self):
        for spans in ([], [[0, 1]], [[2, 1]], [[1, 100]], [[True, 2]], [[1]], [[1, 2], [2, 3]]):
            self.input = copy.deepcopy(self.template_inventory)
            self.input["authorities"][0]["spans"] = spans
            with self.assertRaises(builder.Blocked):
                self.build("full")

    def test_unsafe_and_private_paths(self):
        for path in ("../file.txt", "/file.txt", "C:/file.txt", "dir//file.txt", "dir\\file.txt",
                     "dir/./file.txt", "dir/../file.txt", "nul.txt", "a./file.txt", ".git/file.txt",
                     ".env.json", "private/source.md", "transcripts/review.txt", "credentials.json", "image.png"):
            with self.subTest(path=path), self.assertRaises(builder.Blocked):
                builder.safe_path(path)

    def test_missing_git_file(self):
        with self.blocked("MISSING_SOURCE"):
            self.repo.blob(self.input["head_sha"], "absent.txt")

    def test_mixed_bare_cr_binary_utf8_and_private_content(self):
        private = b"-----BEGIN " + b"RSA PRIVATE KEY-----\n"
        for raw in (b"a\r\nb\n", b"a\rb", b"a\x00b", b"\xff", b"\xef\xbb\xbfa\n",
                    "a\u2028b".encode(), private, b"ghp_" + b"X" * 25):
            with self.subTest(raw=raw[:8]), self.assertRaises(builder.Blocked):
                builder.source_lines(raw)

    def test_rejected_committed_content(self):
        for raw in (b"a\r\nb\n", b"a\x00b", b"\xff"):
            (self.root / "notes.txt").write_bytes(raw)
            head = commit(self.root, "unsupported candidate")
            self.input = inventory(self.root, self.input["base_sha"], head)
            with self.assertRaises(builder.Blocked):
                self.build()

    def test_symlink_submodule_and_type_changes(self):
        for mode in ("120000", "160000"):
            with self.subTest(mode=mode):
                blob = git(self.root, "hash-object", "-w", "--stdin", data=b"notes.txt").decode().strip()
                identity = self.input["base_sha"] if mode == "160000" else blob
                git(self.root, "update-index", "--add", "--cacheinfo", f"{mode},{identity},link.txt")
                git(self.root, "commit", "--no-gpg-sign", "-m", "unsupported mode")
                head = git(self.root, "rev-parse", "HEAD").decode().strip()
                with self.blocked("UNSUPPORTED_GIT_MODE"):
                    self.repo.blob(head, "link.txt")
                git(self.root, "update-index", "--force-remove", "--", "link.txt")
                git(self.root, "commit", "--no-gpg-sign", "-m", "remove unsupported mode")

    def test_deleted_source_included_from_base(self):
        packet, raw_manifest = self.build()
        segment = next(row for row in json.loads(raw_manifest)["segments"] if row["path"] == "removed.txt")
        self.assertEqual(segment["revision"], "base")
        self.assertEqual(packet[segment["packet_offset"]:segment["packet_offset"] + segment["bytes"]], b"Deleted source\n")

    def test_packet_and_manifest_tampering_or_truncation(self):
        packet, manifest = self.build()
        for changed_packet, changed_manifest in ((packet[:-1], manifest), (packet, manifest[:-1]),
                                                 (packet + b"extra", manifest),
                                                 (packet, manifest.replace(b'"packet_bytes":', b'"wrong_bytes":'))):
            with self.assertRaises(builder.Blocked):
                builder.verify(self.repo, self.input, changed_packet, changed_manifest)

    def test_inventory_hash_duplicate_json_and_no_echo(self):
        for raw, digest in ((builder.canonical(self.input), "0" * 64),
                            (b'{"private-value":1,"private-value":2}', None)):
            result = self.cli(input_raw=raw, digest=digest)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            self.assertNotIn(b"private-value", result.stderr)
            self.assertFalse((Path(self.temp.name) / "packet.txt").exists())

    def test_cli_missing_input_and_no_outputs(self):
        self.input["sources"].pop()
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertFalse((Path(self.temp.name) / "packet.txt").exists())
        self.assertFalse((Path(self.temp.name) / "manifest.json").exists())

    def test_existing_output_and_source_writes_blocked(self):
        existing = Path(self.temp.name) / "existing.txt"
        existing.write_bytes(b"keep")
        result = self.cli(packet_path=existing)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(existing.read_bytes(), b"keep")
        for target in (self.root / "new.txt", self.root / ".git" / "new.txt"):
            self.assertEqual(self.cli(packet_path=target).returncode, 2)
            self.assertFalse(target.exists())

    def test_output_collision(self):
        target = Path(self.temp.name) / "same.json"
        self.assertEqual(self.cli(packet_path=target, manifest_path=target).returncode, 2)
        self.assertFalse(target.exists())

    def test_public_review_assertion_and_unexpected_fields(self):
        self.input["public_source_reviewed"] = False
        with self.blocked("SOURCE_REVIEW_REQUIRED"):
            self.build()
        self.input["public_source_reviewed"] = True
        self.input["private_field"] = "must not echo"
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b"must not echo", result.stderr)

    def test_git_blob_integrity_recomputed(self):
        original = self.repo.git

        def corrupt(*args):
            result = original(*args)
            return result + b"truncated replacement" if args[:2] == ("cat-file", "blob") else result

        with patch.object(self.repo, "git", corrupt), self.blocked("GIT_BLOB_MISMATCH"):
            self.repo.blob(self.input["head_sha"], "changed.py")

    def test_no_inherited_git_config_or_replacement_objects(self):
        with patch.dict(os.environ, {"GIT_DIR": "absent", "GIT_CONFIG_COUNT": "1",
                                     "GIT_CONFIG_KEY_0": "alias.status", "GIT_CONFIG_VALUE_0": "!false"}):
            repo = builder.Repository(self.root)
            self.assertEqual(builder.build(repo, self.input, "scoped"), self.build())
        self.assertEqual(self.repo.env["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(self.repo.env["GIT_NO_REPLACE_OBJECTS"], "1")

    def test_git_clean_filter_is_rejected_before_status(self):
        git(self.root, "config", "filter.inject.clean", "unexpected-command")
        with self.blocked("UNSAFE_GIT_FILTER"):
            builder.Repository(self.root)

    def test_unrelated_base_is_rejected(self):
        tree = git(self.root, "rev-parse", self.input["head_sha"] + "^{tree}").decode().strip()
        self.input["base_sha"] = git(self.root, "commit-tree", tree, "-m", "unrelated").decode().strip()
        with self.blocked("GIT_READ_FAILED"):
            self.build()

    def test_invalid_cli_arguments_never_echo(self):
        result = self.cli(extra=("--mode", "private-rejected-value"))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["code"], "INVALID_ARGUMENTS")
        self.assertNotIn(b"private-rejected-value", result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertFalse((Path(self.temp.name) / "packet.txt").exists())
        result = subprocess.run([sys.executable, str(SCRIPT), "build"], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["code"], "INVALID_ARGUMENTS")

    def test_oversized_inventory_blocks_without_output(self):
        result = self.cli(input_raw=b" " * (builder.MAX_INVENTORY_BYTES + 1))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["code"], "INVENTORY_TOO_LARGE")
        self.assertFalse((Path(self.temp.name) / "packet.txt").exists())

    def test_inventory_size_boundary_and_unbounded_packet_reader(self):
        path = Path(self.temp.name) / "limit.json"
        path.write_bytes(b"a" * builder.MAX_INVENTORY_BYTES)
        self.assertEqual(len(builder.read_regular(path, builder.MAX_INVENTORY_BYTES)), builder.MAX_INVENTORY_BYTES)
        path.write_bytes(b"a" * (builder.MAX_INVENTORY_BYTES + 1))
        self.assertEqual(len(builder.read_regular(path)), builder.MAX_INVENTORY_BYTES + 1)

    def test_sha1_blob_identity_is_not_a_fips_security_operation(self):
        original = hashlib.sha1

        def fips_sha1(raw, *, usedforsecurity=True):
            if usedforsecurity:
                raise ValueError("FIPS blocks security SHA-1")
            return original(raw, usedforsecurity=False)

        with patch.object(builder.hashlib, "sha1", fips_sha1):
            self.assertEqual(self.repo.blob(self.input["head_sha"], "changed.py")[0],
                             next(row["blob_sha"] for row in self.input["sources"] if row["path"] == "changed.py"))


if __name__ == "__main__":
    unittest.main()
