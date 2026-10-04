"""Adversarial release and startup boundary checks; no live credentials or providers."""
import copy
from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class FoundationTests(unittest.TestCase):
    def test_s3_file_contract_passes_existing_secret_guard(self):
        spec = importlib.util.spec_from_file_location("security_guard", ROOT.parents[1] / "backend/tests/check_security.py")
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with redirect_stdout(io.StringIO()):
            issues = guard.check_secret_placeholders(str(ROOT))
        self.assertEqual(issues, 0, "foundation file paths must pass the unchanged secret guard")

    def test_only_backend_and_worker_have_outbound_transport(self):
        validator = module("validate")
        config = validator.render_proof()
        self.assertIn("egress", config["networks"])
        self.assertFalse(config["networks"]["egress"].get("internal", False))
        attached = {name for name, service in config["services"].items() if "egress" in service["networks"]}
        self.assertEqual(attached, {"backend", "worker"})
        for mutation in ("isolated", "external", "driver", "data_egress", "missing_egress", "udp", "privileged"):
            invalid = copy.deepcopy(config)
            if mutation == "isolated":
                invalid["networks"]["egress"]["internal"] = True
            elif mutation == "external":
                invalid["networks"]["egress"]["external"] = True
            elif mutation == "driver":
                invalid["networks"]["egress"]["driver"] = "host"
            elif mutation == "data_egress":
                invalid["services"]["postgres"]["networks"]["egress"] = None
            elif mutation == "missing_egress":
                del invalid["services"]["worker"]["networks"]["egress"]
            elif mutation == "udp":
                invalid["services"]["ingress"]["ports"][0]["protocol"] = "udp"
            else:
                invalid["services"]["worker"]["privileged"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validator.check_compose(invalid)
        for name in config["services"]:
            if name == "ingress":
                continue
            invalid = copy.deepcopy(config)
            invalid["services"][name]["ports"] = [{"target": 9000, "published": "9000"}]
            with self.subTest(exposed_service=name), self.assertRaises(ValueError):
                validator.check_compose(invalid)

    def test_s3_slot_preserves_interface_without_vendor_startup(self):
        validator = module("validate")
        config = validator.render_proof()
        self.assertIn("source-artifacts", config["services"])
        slot = config["services"]["source-artifacts"]
        self.assertFalse(slot.get("command"))
        self.assertFalse(slot.get("entrypoint"))
        self.assertFalse(slot.get("environment"))
        for name in ("backend", "worker"):
            environment = config["services"][name]["environment"]
            self.assertEqual(environment["S3_ENDPOINT_URL"], "http://source-artifacts:9000")
            self.assertEqual(environment["S3_BUCKET"], "valora-source-artifacts")
            self.assertEqual(environment["S3_REGION"], "us-east-1")
        manifest = validator.proof_manifest()
        self.assertEqual(manifest["source_artifact_contract"]["runtime_selection"], "deferred")
        invalid_manifest = copy.deepcopy(manifest)
        invalid_manifest["source_artifact_contract"]["runtime_selection"] = "selected"
        with self.assertRaises(ValueError):
            validator.check_manifest(invalid_manifest)
        for mutation in ("command", "entrypoint", "environment", "credentials", "volume", "endpoint", "bucket", "region"):
            invalid = copy.deepcopy(config)
            source = invalid["services"]["source-artifacts"]
            if mutation in ("command", "entrypoint"):
                source[mutation] = ["vendor-specific-startup"]
            elif mutation == "environment":
                source["environment"] = {"VENDOR_ROOT_USER_FILE": "/run/secrets/s3_access_key"}
            elif mutation == "credentials":
                source["secrets"] = []
            elif mutation == "volume":
                source["volumes"][0]["target"] = "/vendor-data"
            else:
                invalid["services"]["backend"]["environment"]["S3_" + {"endpoint": "ENDPOINT_URL", "bucket": "BUCKET", "region": "REGION"}[mutation]] = "invalid"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validator.check_compose(invalid)

    def test_release_rejects_floating_images_and_revision_mismatch(self):
        self.assertTrue((ROOT / "validate.py").is_file(), "release validator missing")
        validator = module("validate")
        manifest = validator.proof_manifest()
        validator.check_manifest(manifest)
        for mutation in ("tag", "revision", "ai"):
            invalid = copy.deepcopy(manifest)
            if mutation == "tag":
                invalid["images"]["backend"]["reference"] = "valora/backend:latest"
            elif mutation == "revision":
                invalid["images"]["frontend"]["revision"] = "b" * 40
            else:
                invalid["images"]["ollama"] = invalid["images"]["backend"]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validator.check_manifest(invalid)

    def test_compose_rejects_database_port_and_external_data_network(self):
        self.assertTrue((ROOT / "validate.py").is_file(), "topology validator missing")
        validator = module("validate")
        config = validator.render_proof()
        validator.check_compose(config)
        for mutation in ("port", "network", "host", "secret"):
            invalid = copy.deepcopy(config)
            if mutation == "port":
                invalid["services"]["postgres"]["ports"] = [{"published": "5432"}]
            elif mutation == "network":
                invalid["networks"]["data"]["internal"] = False
            elif mutation == "host":
                invalid["services"]["backend"]["network_mode"] = "host"
            else:
                invalid["services"]["backend"]["environment"]["POSTGRES_PASSWORD"] = "unsafe"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validator.check_compose(invalid)

    def test_secrets_are_required_and_never_overridden_by_environment(self):
        self.assertTrue((ROOT / "runtime.py").is_file(), "startup secret boundary missing")
        runtime = module("runtime")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            with self.assertRaises(ValueError):
                runtime.load_secrets(root)
            for name in runtime.SECRETS:
                (root / name).write_text("a" * 48, encoding="utf-8")
            os.environ["POSTGRES_PASSWORD"] = "ambient-value"
            runtime.load_secrets(root)
            self.assertEqual(os.environ["POSTGRES_PASSWORD"], "a" * 48)
            (root / "postgres_password").write_text("contains@url:syntax", encoding="utf-8")
            with self.assertRaises(ValueError):
                runtime.load_secrets(root)

    def test_startup_rejects_http_wildcards_and_schema_omission(self):
        self.assertTrue((ROOT / "runtime.py").is_file(), "startup config boundary missing")
        runtime = module("runtime")
        valid = {
            "VALORA_ENV": "production", "BACKEND_CORS_ORIGINS": "https://valora.example.invalid",
            "DOCUMENT_BLOB_PROVIDER": "local", "DOCUMENT_BLOB_ROOT": "/var/lib/valora/blobs",
            "VALORA_SCHEMA_HEAD": "b5c6d7e8f9a0",
        }
        for value in ("http://valora.example.invalid", "*", "https://host/path", "https://host,https://other"):
            with patch.dict(os.environ, {**valid, "BACKEND_CORS_ORIGINS": value}, clear=True):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    runtime.check_config()
        with patch.dict(os.environ, valid, clear=True):
            runtime.check_config()
            del os.environ["VALORA_SCHEMA_HEAD"]
            with self.assertRaises(ValueError):
                runtime.check_config()


if __name__ == "__main__":
    unittest.main()
