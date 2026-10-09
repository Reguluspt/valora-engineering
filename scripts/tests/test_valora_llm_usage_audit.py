"""Sanitized metadata, measurement and executable CLI regressions; no provider requests."""

import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "valora_llm_usage_audit.py"
FIXTURES = Path(__file__).parent / "fixtures" / "valora_llm_usage_audit"
spec = importlib.util.spec_from_file_location("usage_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def events():
    return json.loads((FIXTURES / "a18_a19.json").read_text(encoding="utf-8"))["events"]


def document(rows):
    return {"schema_version": "1.0", "sanitized_metadata": True, "events": rows}


class MeasurementTests(unittest.TestCase):
    def test_historical_controls(self):
        result = audit.audit(events())
        by_id = {row["event_id"]: row for row in result["rows"]}
        self.assertEqual(result["status"], "WARN")
        self.assertEqual(result["gate_authority"], "NONE")
        self.assertEqual(result["comparison"], "NOT COMPARABLE")
        self.assertEqual([by_id[f"e-{i:08x}"]["review_completeness"] for i in (1, 2, 3)],
                         ["INCOMPLETE", "INCOMPLETE", "COMPLETE"])
        self.assertEqual(by_id["e-00000005"]["input"], 12000)
        self.assertEqual(by_id["e-00000005"]["output"], 400)
        review = by_id["e-00000007"]
        self.assertEqual([review[key] for key in audit.COUNTERS],
                         [384638, 350464, 0, 4309, 993, 388947])
        self.assertIsNone(review["uncached"])
        self.assertEqual(by_id["e-00000008"]["cost_classification"], "NOT MEASURABLE")
        self.assertFalse(any(row["model"] == "gpt-6-luna" and row["pr"] == 156
                             for row in result["rows"]))
        self.assertNotIn("session_id", review)

    def test_provider_input_cache_and_reasoning(self):
        ds = audit.audit([events()[0]])["rows"][0]
        self.assertEqual(ds["uncached"], 600)
        gm = audit.audit([events()[-1]])["rows"][0]
        self.assertEqual((gm["uncached"], gm["output"], gm["reasoning"], gm["total"]),
                         (80, 10, 5, 115))
        op = events()[7]
        op.update(usage_format="openai_responses", usage={"input_tokens":100,
                  "cached_tokens":30,"cache_write_tokens":20,"output_tokens":10,
                  "reasoning_tokens":4,"total_tokens":110})
        self.assertEqual(audit.audit([op])["rows"][0]["uncached"], 50)
        del op["usage"]["cache_write_tokens"]
        self.assertIsNone(audit.audit([op])["rows"][0]["uncached"])

    def test_complete_applicable_counters_and_explicit_output_semantics(self):
        report = audit.audit(events())
        rows = {row["event_id"]:row for row in report["rows"]}
        for event_id in ("e-00000001", "e-00000006", "e-00000007", "e-00000009"):
            self.assertNotIn("PARTIAL_TOKEN_MEASUREMENT", rows[event_id]["warnings"])
        self.assertEqual(rows["e-00000001"]["output_semantics"], "INCLUDES_REASONING")
        self.assertEqual(rows["e-00000009"]["output_semantics"], "EXCLUDES_REASONING")
        self.assertEqual(rows["e-00000006"]["output_semantics"], "UNKNOWN")
        self.assertEqual(rows["e-00000006"]["review_completeness"], "NOT_APPLICABLE")
        self.assertEqual(rows["e-00000008"]["review_completeness"], "NOT_APPLICABLE")
        self.assertIn("UNCACHED_NOT_MEASURABLE", rows["e-00000007"]["warnings"])
        self.assertTrue(all("output_semantics" in group for group in report["phase_totals"]))

    def test_missing_counters_never_become_zero(self):
        record = events()[0]
        record["usage"] = {}
        report = audit.audit([record])
        self.assertTrue(all(report["rows"][0][key] is None for key in audit.COUNTERS))
        self.assertIsNone(report["phase_totals"][0]["input"])

    def test_unknown_runner_semantics_preserve_uncertainty(self):
        row = events()[3]
        row["usage"].update(input=10, cached=500, total=None)
        result = audit.audit([row])["rows"][0]
        self.assertIsNone(result["uncached"])
        self.assertIn("CACHE_SEMANTICS_UNKNOWN", result["warnings"])

    def test_cache_write_total_and_cumulative_cost_rejection(self):
        row = events()[7]
        row.update(usage_format="openai_responses", usage={"input_tokens":100,
                   "cached_tokens":80,"cache_write_tokens":30,"output_tokens":1,
                   "reasoning_tokens":0,"total_tokens":101})
        with self.assertRaises(audit.Blocked):
            audit.audit([row])
        row = events()[3]
        row["cost"] = {"amount":"1","currency":"USD","source":"billing-"+"a"*64,
                       "original_charge":True}
        with self.assertRaises(audit.Blocked):
            audit.audit([row])
        row = events()[3]
        row["origin"] = None
        with self.assertRaises(audit.Blocked):
            audit.audit([row])

    def test_tool_completion_and_unknown_identity_never_certify(self):
        row = events()[2]
        row.update(finish_reason="tool_calls", model_identity="ACTUAL_MODEL_UNVERIFIED")
        result = audit.audit([row])["rows"][0]
        self.assertEqual(result["review_completeness"], "UNKNOWN")
        self.assertIn("ACTUAL_MODEL_UNVERIFIED", result["warnings"])

    def test_cumulative_origin_missing_baseline_and_repeated_snapshot(self):
        rows = events()[3:5]
        rows[0]["origin"] = "UNAVAILABLE"
        result = audit.audit(rows)
        self.assertIsNone(result["rows"][0]["input"])
        self.assertEqual(result["rows"][1]["input"], 12000)
        self.assertIsNone(result["phase_totals"][0]["input"])
        rows[1]["usage"] = copy.deepcopy(rows[0]["usage"])
        repeat = audit.audit(rows)["rows"][1]
        self.assertEqual(repeat["input"], 0)
        self.assertIn("REPEATED_SNAPSHOT_ZERO_CONTRIBUTION", repeat["warnings"])

    def test_timestamps_compare_instants_with_fractional_seconds(self):
        rows = events()[3:5]
        rows[0]["timestamp"] = "2026-10-08T15:00:00Z"
        rows[1]["timestamp"] = "2026-10-08T15:00:00.1Z"
        self.assertEqual(audit.audit(rows)["rows"][1]["input"], 12000)

    def test_delta_report_is_explicitly_not_reconstructed(self):
        row = events()[0]
        row.update(snapshot_kind="delta", origin="e-000000ff")
        self.assertIn("SOURCE_REPORTED_DELTA_NOT_RECONSTRUCTED",
                      audit.audit([row])["rows"][0]["warnings"])

    def test_duplicate_delta_origin_and_reasoning_increment_block(self):
        rows = events()[0:2]
        for row in rows:
            row.update(snapshot_kind="delta", origin="e-000000ff")
        with self.assertRaises(audit.Blocked):
            audit.audit(rows)
        rows = events()[5:7]
        rows[1]["usage"].update(output_tokens=51, reasoning_output_tokens=31,
                               total_tokens=408511)
        with self.assertRaises(audit.Blocked):
            audit.audit(rows)

    def test_length_cannot_be_promoted_by_report_pass(self):
        row = events()[0]
        row.update(report_state="COMPLETE", quality="REPORTED_PASS")
        result = audit.audit([row])["rows"][0]
        self.assertEqual(result["review_completeness"], "INCOMPLETE")
        self.assertEqual(result["status"], "WARN")

    def test_original_charge_retained_without_cost_comparison(self):
        row = events()[0]
        row["cost"] = {"amount":"0.00123","currency":"USD","source":"billing-" + "1"*64,
                       "original_charge":True}
        result = audit.audit([row])
        self.assertEqual(result["rows"][0]["cost_amount"], "0.00123")
        self.assertEqual(result["rows"][0]["cost_classification"],
                         "SOURCE_ASSERTED_ORIGINAL_CHARGE")
        self.assertEqual(result["phase_totals"][0]["cost_classification"], "NOT COMPARABLE")

    def test_negative_counters_cache_provenance_and_identity(self):
        mutations = [
            ("negative", lambda row: row["usage"].update(prompt_tokens=-1)),
            ("boolean", lambda row: row["usage"].update(prompt_tokens=True)),
            ("float", lambda row: row["usage"].update(prompt_tokens=1.5)),
            ("cached", lambda row: row["usage"].update(prompt_cache_hit_tokens=1001)),
            ("cache_split", lambda row: row["usage"].update(prompt_cache_miss_tokens=2)),
            ("reasoning", lambda row: row["usage"].update(reasoning_tokens=32001)),
            ("total", lambda row: row["usage"].update(total_tokens=3)),
            ("provider", lambda row: row.update(provider="google")),
            ("format", lambda row: row.update(usage_format="unknown")),
            ("missing_origin", lambda row: row.pop("usage_source")),
            ("source", lambda row: row.update(usage_source="file:///private")),
            ("timestamp", lambda row: row.update(timestamp="2026-99-99T12:00:00Z")),
            ("unverified_cost", lambda row: row.update(cost={"amount":"1","currency":"USD",
                "source":"billing-" + "1"*64,"original_charge":False})),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                row = events()[0]
                mutate(row)
                with self.assertRaises(audit.Blocked):
                    audit.audit([row])
        for key in ("candidate_sha", "packet_sha256", "packet_bytes", "base_sha"):
            rows = events()[3:5]
            rows[1][key] = 10 if key == "packet_bytes" else "f" * len(rows[1][key])
            with self.subTest(key=key), self.assertRaises(audit.Blocked):
                audit.audit(rows)

    def test_nonmonotonic_duplicate_and_mixed_counter_streams(self):
        for change in ("decrease", "origin", "duplicate_id", "sequence", "mixed", "timestamp"):
            rows = events()[3:5]
            if change == "decrease":
                rows[1]["usage"]["input"] = 1
            elif change == "origin":
                rows[1]["origin"] = "e-000000ff"
            elif change == "duplicate_id":
                rows[1]["event_id"] = rows[0]["event_id"]
            elif change == "sequence":
                rows[1]["sequence"] = rows[0]["sequence"]
            elif change == "mixed":
                rows[1]["snapshot_kind"] = "delta"
            else:
                rows[1]["timestamp"] = rows[0]["timestamp"]
            with self.subTest(change=change), self.assertRaises(audit.Blocked):
                audit.audit(rows)

    def test_expected_head_packet_and_cross_session_identity(self):
        rows = events()[0:3]
        with self.assertRaises(audit.Blocked):
            audit.audit(rows, expected_head="f" * 40)
        with self.assertRaises(audit.Blocked):
            audit.audit(rows, expected_packet="f" * 64)
        rows[1].update(session_id="different-session", candidate_sha="f"*40)
        with self.assertRaises(audit.Blocked):
            audit.audit(rows)

    def test_json_csv_golden_and_input_order(self):
        report = audit.audit(events())
        self.assertEqual(audit.json_report(report),
                         (FIXTURES / "expected.json").read_text(encoding="utf-8"))
        self.assertEqual(audit.csv_report(report),
                         (FIXTURES / "expected.csv").read_text(encoding="utf-8"))
        self.assertEqual(report, audit.audit(list(reversed(events()))))
        csv_rows = list(csv.DictReader(io.StringIO(audit.csv_report(report))))
        self.assertEqual(len(csv_rows), 9)
        self.assertTrue(all(row["cost_amount"] == "" for row in csv_rows))


class CliTests(unittest.TestCase):
    def invoke(self, path, *arguments):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(path), *map(str, arguments)],
                              text=True, capture_output=True, timeout=15)

    def test_executable_json_csv_and_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out_json, out_csv = root / "report.json", root / "report.csv"
            run = self.invoke(FIXTURES / "a18_a19.json", "--json-out", out_json, "--csv-out", out_csv)
            self.assertEqual((run.returncode, run.stdout, run.stderr), (1, "", ""))
            self.assertEqual(out_json.read_bytes(), (FIXTURES / "expected.json").read_bytes())
            self.assertEqual(out_csv.read_bytes(), (FIXTURES / "expected.csv").read_bytes())
            jsonl = root / "events.jsonl"
            jsonl.write_text("\n".join(json.dumps({"schema_version":"1.0",
                "sanitized_metadata":True,"event":event}) for event in events())+"\n", encoding="utf-8")
            run = self.invoke(jsonl)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(run.stdout, (FIXTURES / "expected.json").read_text(encoding="utf-8"))

    def test_privacy_rejection_does_not_echo_keys_values_or_paths(self):
        for field in ("prompt", "reasoning_content", "transcript", "api_key", "customer_appraisal"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                row = events()[0]
                row[field] = "synthetic-sensitive-marker-do-not-echo"
                source = root / "sensitive-path-marker.json"
                source.write_text(json.dumps(document([row])), encoding="utf-8")
                out = root / "out.json"
                run = self.invoke(source, "--json-out", out)
                self.assertEqual(run.returncode, 2)
                self.assertFalse(out.exists())
                self.assertEqual(json.loads(run.stderr), {"status":"BLOCKED","code":"UNEXPECTED_FIELD"})
                for forbidden in (field, "synthetic-sensitive-marker", "sensitive-path-marker", directory):
                    self.assertNotIn(forbidden, run.stdout + run.stderr)
                self.assertEqual(run.stdout, "")

    def test_nested_sensitive_fields_and_corrupt_json(self):
        row = events()[0]
        row["usage"]["raw_reasoning"] = "synthetic-sensitive-marker"
        cases = [json.dumps(document([row])), '{"schema_version":"1.0","schema_version":"1.0"}',
                 '{"private":"synthetic-sensitive-marker",', "[NaN]", "[" * 2000]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.json"
            for content in cases:
                source.write_text(content, encoding="utf-8")
                run = self.invoke(source)
                self.assertEqual(run.returncode, 2)
                self.assertNotIn("synthetic-sensitive-marker", run.stderr)
                self.assertEqual(run.stdout, "")

    def test_output_collisions_never_overwrite_existing_input_or_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            original = json.dumps(document(events()))
            source.write_text(original, encoding="utf-8")
            existing = root / "existing.json"
            existing.write_text("preserve", encoding="utf-8")
            for args in (("--json-out", source), ("--json-out", existing),
                         ("--json-out", root/"same", "--csv-out", root/"same")):
                run = self.invoke(source, *args)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(source.read_text(encoding="utf-8"), original)
                self.assertEqual(existing.read_text(encoding="utf-8"), "preserve")

    def test_missing_envelope_oversize_empty_and_unknown_version(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.json"
            for content in (json.dumps(events()), json.dumps(document([])),
                            json.dumps({**document(events()), "schema_version":"2.0"}),
                            " "*(audit.MAX_BYTES+1)):
                source.write_text(content, encoding="utf-8")
                self.assertEqual(self.invoke(source).returncode, 2)

    def test_zero_exit_means_observed_not_certified(self):
        row = events()[0]
        row.update(usage_format="openai_responses", provider="openai", model="gpt-6-luna",
                   phase="implementation", finish_reason="completed", report_state="NOT_APPLICABLE",
                   usage={"input_tokens":10,"cached_tokens":0,"cache_write_tokens":0,
                          "output_tokens":2,"reasoning_tokens":0,"total_tokens":12},
                   cost={"amount":"0.01","currency":"USD","source":"billing-"+"a"*64,
                         "original_charge":True})
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "observed.json"
            source.write_text(json.dumps(document([row])), encoding="utf-8")
            result = self.invoke(source)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["gate_authority"], "NONE")

    def test_invalid_cli_arguments_are_not_echoed(self):
        result = self.invoke(FIXTURES / "a18_a19.json", "--synthetic-sensitive-marker")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr), {"status":"BLOCKED","code":"INVALID_ARGUMENTS"})
        self.assertNotIn("synthetic-sensitive-marker", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
