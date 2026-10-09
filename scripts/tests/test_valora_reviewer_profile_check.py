"""Synthetic adversarial receipts and actual offline CLI integration."""

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "valora_reviewer_profile_check.py"
FIXTURES = Path(__file__).parent / "fixtures" / "valora_reviewer_profile"
spec = importlib.util.spec_from_file_location("reviewer_profile", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def load(name="complete.json"):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def pins(document):
    expected = copy.deepcopy(document["expected"])
    for field in ("changed_files", "authorities"):
        expected[field].sort(key=lambda row: row["path"])
    encoded = (json.dumps(expected, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    identity = expected["identity"]
    return [identity["base_sha"], identity["head_sha"], identity["packet_sha256"], hashlib.sha256(encoded).hexdigest()]


def modify(document, operations):
    for operation in operations:
        tokens = operation["path"].strip("/").split("/")
        parent = document
        for token in tokens[:-1]:
            parent = parent[int(token)] if isinstance(parent, list) else parent[token]
        last = int(tokens[-1]) if isinstance(parent, list) else tokens[-1]
        if operation["op"] == "delete":
            del parent[last]
        else:
            parent[last] = operation["value"]
    return document


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.document = load()

    def check(self, document=None):
        document = self.document if document is None else document
        return checker.check(document, *pins(self.document))

    def test_complete_is_not_gate_pass(self):
        result = self.check()
        self.assertEqual(result["mechanical_preflight"], "COMPLETE")
        self.assertEqual(result["gate_authority"], "NONE")
        self.assertEqual(result["evidence_authenticity"], "SOURCE_ASSERTED_NOT_AUTHENTICATED")
        self.assertNotIn("PASS", json.dumps(result))

    def test_substantive_findings_are_complete_without_acceptance(self):
        result = self.check(load("with_findings.json"))
        self.assertEqual(result["mechanical_preflight"], "COMPLETE")
        self.assertEqual(result["attempts"][0]["findings_count"], 1)
        self.assertEqual(result["gate_authority"], "NONE")

    def test_negative_controls(self):
        for case in load("negative_cases.json"):
            with self.subTest(case=case["name"]):
                document = modify(copy.deepcopy(self.document), case["patches"])
                if case["exit"] == 2:
                    with self.assertRaises(checker.Invalid):
                        self.check(document)
                else:
                    self.assertEqual(self.check(document)["mechanical_preflight"], case["state"])

    def test_a19_preserves_length_length_stop_and_gemini_correction(self):
        result = self.check(load("a19_attempts.json"))
        self.assertEqual(result["mechanical_preflight"], "COMPLETE")
        self.assertEqual([x["mechanical_preflight"] for x in result["attempts"]],
                         ["INCOMPLETE", "INCOMPLETE", "COMPLETE", "UNKNOWN", "COMPLETE"])
        self.assertEqual(len(result["attempts"]), 5)

    def test_retry_without_approval_stays_incomplete_after_later_success(self):
        document = load("a19_attempts.json")
        document["attempts"][1]["retry"] = None
        result = self.check(document)
        self.assertEqual(result["mechanical_preflight"], "INCOMPLETE")
        self.assertIn("RETRY_HISTORY_INVALID", result["codes"])

    def test_unverified_settings_change_blocks_history(self):
        document = load("a19_attempts.json")
        document["attempts"][2]["retry"]["settings_changed"] = True
        self.assertEqual(self.check(document)["mechanical_preflight"], "INCOMPLETE")

    def test_retry_reason_must_match_predecessor(self):
        document = load("a19_attempts.json")
        document["attempts"][2]["retry"]["reason"] = "MODEL_IDENTITY_CORRECTION"
        self.assertEqual(self.check(document)["mechanical_preflight"], "INCOMPLETE")

    def test_retry_chain_cannot_discard_attempt_or_skip_number(self):
        document = load("a19_attempts.json")
        del document["attempts"][1]
        with self.assertRaises(checker.Invalid):
            self.check(document)

    def test_contaminated_session_cannot_be_cleared_by_later_flag(self):
        document = load("a19_attempts.json")
        document["attempts"][0]["independence"]["peer_reports_seen"] = True
        result = self.check(document)
        self.assertEqual(result["mechanical_preflight"], "INCOMPLETE")
        self.assertIn("CONTAMINATED_SESSION_REUSED", result["codes"])

    def test_unknown_earlier_isolation_cannot_be_silently_cleared(self):
        document = load("a19_attempts.json")
        document["attempts"][0]["independence"]["evidence_sha256"] = None
        self.assertIn("SESSION_ISOLATION_HISTORY_UNVERIFIED", self.check(document)["codes"])

    def test_retry_cannot_drop_or_downgrade_material_findings(self):
        document = load("with_findings.json")
        previous = document["attempts"][0]
        later = copy.deepcopy(previous)
        previous["report"]["sections"].pop()
        later.update(id="a-00000002", attempt=2,
                     retry={"previous_attempt_id": previous["id"], "reason": "REPORT_INCOMPLETE",
                            "approval_ref": "SYNTHETIC", "settings_changed": False})
        document["attempts"].append(later)
        self.assertEqual(self.check(document)["mechanical_preflight"], "COMPLETE")
        for downgrade in (False, True):
            with self.subTest(downgrade=downgrade):
                case = copy.deepcopy(document)
                final = case["attempts"][-1]["report"]
                if downgrade:
                    final["findings"][0]["severity"] = "P2"
                    final["severity_checks"][2]["state"] = "FINDINGS"
                else:
                    final["findings"] = []
                final["severity_checks"][1]["state"] = "NONE"
                result = self.check(case)
                self.assertEqual(result["mechanical_preflight"], "INCOMPLETE")
                self.assertIn("FINDING_HISTORY_LOST_OR_DOWNGRADED", result["codes"])

    def test_terminal_label_is_not_deepseek_provider_finish(self):
        self.document["attempts"][0]["native"]["finish_reason"] = "completed"
        self.assertEqual(self.check()["mechanical_preflight"], "UNKNOWN")

    def test_later_failure_invalidates_earlier_completion(self):
        later = copy.deepcopy(self.document["attempts"][0])
        later.update(id="a-00000002", attempt=2,
                     retry={"previous_attempt_id": "a-00000001", "reason": "FINISH_LENGTH",
                            "approval_ref": "SYNTHETIC", "settings_changed": False})
        later["native"]["finish_reason"] = "length"
        self.document["attempts"].append(later)
        self.assertEqual(self.check()["mechanical_preflight"], "INCOMPLETE")

    def test_stale_history_cannot_be_hidden_by_current_success(self):
        document = load("a19_attempts.json")
        document["attempts"][0]["identity"]["head_sha"] = "9" * 40
        result = self.check(document)
        self.assertEqual(result["mechanical_preflight"], "INCOMPLETE")
        self.assertIn("SOURCE_HISTORY_MIXED", result["codes"])

    def test_gemini_unexposed_finish_requires_separate_terminal_evidence(self):
        self.assertEqual(self.check()["mechanical_preflight"], "COMPLETE")
        self.document["attempts"][1]["native"]["terminal_evidence_sha256"] = None
        self.assertEqual(self.check()["mechanical_preflight"], "UNKNOWN")

    def test_offline_domain_na_requires_evidence_and_reason(self):
        axis = self.document["attempts"][0]["report"]["coverage"][4]
        axis.update(state="N/A", rationale="NO_RUNTIME_CHANGE")
        self.assertEqual(self.check()["mechanical_preflight"], "COMPLETE")
        axis["evidence_sha256"] = None
        self.assertEqual(self.check()["mechanical_preflight"], "INCOMPLETE")

    def test_finding_lines_must_be_in_transported_source(self):
        for path, start, end in (("absent.py", 1, 1), ("changed.py", 39, 41),
                                 ("CODEX.md", 21, 22), ("CODEX.md", 19, 41)):
            with self.subTest(path=path, start=start):
                document = load("with_findings.json")
                document["attempts"][0]["report"]["findings"][0].update(path=path, start=start, end=end)
                self.assertEqual(self.check(document)["mechanical_preflight"], "INCOMPLETE")
        document = load("with_findings.json")
        document["attempts"][0]["report"]["findings"][0].update(path="CODEX.md", start=8, end=20)
        self.assertEqual(self.check(document)["mechanical_preflight"], "COMPLETE")

    def test_case_colliding_and_duplicate_source_rows_block(self):
        duplicate = copy.deepcopy(self.document["attempts"][0]["report"]["changed_files"][0])
        duplicate["path"] = "CHANGED.py"
        self.document["attempts"][0]["report"]["changed_files"].append(duplicate)
        with self.assertRaises(checker.Invalid):
            self.check()

    def test_expected_source_inventory_is_independently_pinned(self):
        document = copy.deepcopy(self.document)
        document["expected"]["authorities"][0]["spans"][0][0] = 9
        with self.assertRaises(checker.Invalid):
            self.check(document)

    def test_expected_sha_pins_cannot_be_silently_replaced(self):
        for index, length in ((0, 40), (1, 40), (2, 64), (3, 64)):
            with self.subTest(pin=index):
                values = pins(self.document)
                values[index] = "9" * length
                with self.assertRaises(checker.Invalid):
                    checker.check(self.document, *values)

    def test_permutations_keep_deterministic_output(self):
        document = load("a19_attempts.json")
        original = checker.canonical(self.check(document))
        document["attempts"].reverse()
        for attempt in document["attempts"]:
            if attempt["report"]:
                for field in ("sections", "coverage", "severity_checks", "authorities", "changed_files"):
                    attempt["report"][field].reverse()
        document["expected"]["authorities"].reverse()
        self.assertEqual(checker.canonical(self.check(document)), original)

    def test_a19_usage_retains_certified_counter_semantics(self):
        metrics_path = SCRIPT.parent / "valora_llm_usage_audit.py"
        metrics_spec = importlib.util.spec_from_file_location("usage_audit", metrics_path)
        metrics = importlib.util.module_from_spec(metrics_spec)
        metrics_spec.loader.exec_module(metrics)
        result = metrics.audit(metrics.read_metadata(FIXTURES / "a19_usage.json"))
        rows = result["rows"]
        self.assertEqual([r["review_completeness"] for r in rows if r["provider"] == "deepseek"],
                         ["INCOMPLETE", "INCOMPLETE", "COMPLETE"])
        google = [r for r in rows if r["provider"] == "google"]
        self.assertEqual(len(google), 2)
        self.assertTrue(all(r["cache_semantics"] == "UNKNOWN" for r in google))
        self.assertEqual([r["input"] for r in google], [10000, 12000])
        self.assertEqual(sum(r["input"] for r in google), 22000)
        self.assertTrue(all(r["uncached"] is None for r in google))
        self.assertTrue(all(r["cost_classification"] == "NOT MEASURABLE" for r in google))
        self.assertEqual(result["gate_authority"], "NONE")

    def test_static_offline_import_boundary(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        imports = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
        imports |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertLessEqual(imports, {"argparse", "hashlib", "json", "pathlib", "re", "sys"})
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(calls & {"write_text", "write_bytes", "unlink", "rename", "replace", "mkdir", "connect", "system", "getenv"})


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.document = load()
        self.input = self.root / "sanitized.json"

    def cli(self, document=None, raw=None, extra=(), values=None, input_path=None):
        if input_path is None:
            self.input.write_bytes(raw if raw is not None else json.dumps(
                self.document if document is None else document).encode())
        values = pins(self.document) if values is None else values
        flags = ("--expected-base", "--expected-head", "--expected-packet", "--expected-inventory")
        args = [sys.executable, str(SCRIPT), str(self.input if input_path is None else input_path)]
        for flag, value in zip(flags, values):
            args.extend([flag, value])
        existing = set(self.root.iterdir())
        result = subprocess.run(args + list(extra), capture_output=True, timeout=15, cwd=self.root,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(set(self.root.iterdir()), existing)
        return result

    def test_actual_cli_complete_and_findings(self):
        for name in ("complete.json", "with_findings.json", "a19_attempts.json"):
            with self.subTest(fixture=name):
                result = self.cli(load(name))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, b"")
                output = json.loads(result.stdout)
                self.assertEqual(output["mechanical_preflight"], "COMPLETE")
                self.assertEqual(output["gate_authority"], "NONE")
                self.assertNotIn(b"PASS", result.stdout)

    def test_all_negative_cases_through_actual_cli(self):
        for case in load("negative_cases.json"):
            with self.subTest(case=case["name"]):
                result = self.cli(modify(copy.deepcopy(self.document), case["patches"]))
                self.assertEqual(result.returncode, case["exit"])
                output = json.loads(result.stderr if case["exit"] == 2 else result.stdout)
                self.assertEqual(output["mechanical_preflight"], case["state"])
                self.assertEqual(output["gate_authority"], "NONE")
                self.assertNotIn(b"REJECTED_SYNTHETIC_CONTENT", result.stdout + result.stderr)
                self.assertNotIn(str(self.root).encode(), result.stdout + result.stderr)
                if case["exit"] == 2:
                    self.assertEqual(result.stdout, b"")

    def test_json_and_argument_errors_never_echo_rejected_text(self):
        for raw in (b'{"private":"REJECTED_SYNTHETIC_CONTENT",', b'{"x":1,"x":2}',
                    b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'[]'):
            with self.subTest(raw=raw):
                result = self.cli(raw=raw)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertNotIn(b"REJECTED_SYNTHETIC_CONTENT", result.stderr)
        result = self.cli(extra=("--REJECTED_SYNTHETIC_CONTENT",))
        self.assertEqual(json.loads(result.stderr)["code"], "INVALID_ARGUMENTS")
        self.assertNotIn(b"REJECTED_SYNTHETIC_CONTENT", result.stderr)

    def test_oversize_input_blocks_before_parsing(self):
        result = self.cli(raw=b" " * 2_000_001)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["code"], "INPUT_TOO_LARGE")

    def test_unavailable_input_is_safe(self):
        result = self.cli(input_path=self.root / "REJECTED_SYNTHETIC_CONTENT.json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"REJECTED_SYNTHETIC_CONTENT", result.stderr)

    def test_symlink_policy_rejects_before_read(self):
        self.input.write_text(json.dumps(self.document), encoding="utf-8")
        with patch.object(Path, "is_symlink", return_value=True), patch.object(Path, "open") as opened:
            with self.assertRaises(checker.Invalid):
                checker.read_document(self.input)
            opened.assert_not_called()

    def test_unpinned_cli_cannot_emit_partial_success(self):
        values = pins(self.document)
        values[1] = "9" * 40
        result = self.cli(values=values)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(json.loads(result.stderr)["code"], "EXPECTED_IDENTITY_MISMATCH")

    def test_certified_metrics_cli_on_synthetic_history(self):
        result = subprocess.run([sys.executable, str(SCRIPT.parent / "valora_llm_usage_audit.py"),
                                 str(FIXTURES / "a19_usage.json")], capture_output=True, timeout=15,
                                cwd=self.root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["gate_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
